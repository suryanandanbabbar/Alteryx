"""Download endpoints for generating and streaming export artifacts."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from awa.generators.svg_generator import generate_svg
from awa.generators.docx_generator import generate_docx
from awa.generators.doc_builder import build_document_model
from awa.generators.python_generator import generate_python_code
from awa.generators.sttm_generator import generate_sttm_excel
from awa.generators.tool_specifications_generator import generate_tool_specifications_excel
from awa.model.tool_specifications import build_tool_specifications_document
from awa.analysis.sttm_extractor import extract_sttm
from awa.llm.generator import get_default_generator
from backend.app.services.storage import get_storage

router = APIRouter(prefix="/download", tags=["Download"])


def _get_result_or_404(analysis_id: str):
    storage = get_storage()
    result = storage.get(analysis_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found or session has expired.",
        )
    return result


@router.get("/{analysis_id}/sttm")
def download_sttm(analysis_id: str):
    """Download the Source-to-Target Mapping (.xlsx) workbook for the workflow."""
    res = _get_result_or_404(analysis_id)
    sttm_doc = res.sttm or extract_sttm(res.workflow, res.graph, res.business_summary)

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        tmp_path = Path(tf.name)

    try:
        generate_sttm_excel(sttm_doc, tmp_path)
        xlsx_bytes = tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    filename = f"{res.workflow.metadata.name or 'workflow'}_STTM.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/docx")
def download_docx(analysis_id: str):
    """Download the executive Business Report Word document (.docx) for the workflow."""
    res = _get_result_or_404(analysis_id)
    svg_str = generate_svg(res.dag_layout)
    doc_model = build_document_model(
        res.workflow,
        res.execution_order,
        res.translations,
        res.dag_layout,
        res.lineage_paths,
        business_summary=res.business_summary,
        analysis_id=res.analysis_id,
        graph=res.graph,
    )

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        tmp_path = Path(tf.name)

    try:
        generate_docx(doc_model, tmp_path, svg_content=svg_str)
        docx_bytes = tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    base_name = res.workflow.metadata.name or "workflow"
    filename = f"{base_name}_Business_Report.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/tool-specifications")
@router.get("/{analysis_id}/technical-docx")
def download_tool_specifications(analysis_id: str):
    """Download the Tool Specifications Excel workbook (.xlsx) for the workflow."""
    res = _get_result_or_404(analysis_id)

    gen = get_default_generator()
    tool_specs = gen.generate_all_tool_specifications(
        res.workflow,
        graph=res.graph,
        workflow_id=res.analysis_id,
    )

    tool_doc = build_tool_specifications_document(
        workflow=res.workflow,
        graph=res.graph,
        tool_specs=tool_specs,
    )

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        tmp_path = Path(tf.name)

    try:
        generate_tool_specifications_excel(tool_doc, tmp_path)
        xlsx_bytes = tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    base_name = res.workflow.metadata.name or "workflow"
    filename = f"{base_name}_Tool_Specifications.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/json")
def download_json(analysis_id: str):
    """Download the structured workflow JSON file."""
    res = _get_result_or_404(analysis_id)
    data = res.to_dict()
    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    filename = f"{res.workflow.metadata.name or 'workflow'}.json"

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/python")
def download_python(analysis_id: str):
    """Download the Python translation (.py) for the workflow."""
    res = _get_result_or_404(analysis_id)
    py_code, _, _ = generate_python_code(
        res.workflow,
        res.execution_order,
        res.translations,
        res.consumed_anchors,
    )
    filename = f"{res.workflow.metadata.name or 'workflow'}.py"

    return Response(
        content=py_code.encode("utf-8"),
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/svg")
def download_svg(analysis_id: str):
    """Download the standalone SVG workflow diagram."""
    res = _get_result_or_404(analysis_id)
    svg_content = generate_svg(res.dag_layout)
    filename = f"{res.workflow.metadata.name or 'workflow'}.svg"

    return Response(
        content=svg_content.encode("utf-8"),
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/zip")
def download_zip(analysis_id: str):
    """Download a single ZIP bundle containing all generated outputs."""
    res = _get_result_or_404(analysis_id)
    base_name = res.workflow.metadata.name or "workflow"

    # 1. JSON
    data = res.to_dict()
    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

    # 2. Python
    py_code, _, _ = generate_python_code(
        res.workflow,
        res.execution_order,
        res.translations,
        res.consumed_anchors,
    )
    py_bytes = py_code.encode("utf-8")

    # 3. SVG
    svg_str = generate_svg(res.dag_layout)
    svg_bytes = svg_str.encode("utf-8")

    # 4. Diagnostics JSON
    diags_data = {
        "diagnostics": [d.to_dict() for d in res.diagnostics],
        "support_summary": res.metrics.support_summary,
    }
    diags_bytes = json.dumps(diags_data, indent=2, ensure_ascii=False).encode("utf-8")

    # 5. Business Report DOCX
    doc_model = build_document_model(
        res.workflow,
        res.execution_order,
        res.translations,
        res.dag_layout,
        res.lineage_paths,
        business_summary=res.business_summary,
        analysis_id=res.analysis_id,
        graph=res.graph,
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf_biz:
        tmp_biz_path = Path(tf_biz.name)
    try:
        generate_docx(doc_model, tmp_biz_path, svg_content=svg_str)
        biz_docx_bytes = tmp_biz_path.read_bytes()
    finally:
        if tmp_biz_path.exists():
            tmp_biz_path.unlink()

    # 6. Tool Specifications XLSX
    gen = get_default_generator()
    tool_specs = gen.generate_all_tool_specifications(
        res.workflow,
        graph=res.graph,
        workflow_id=res.analysis_id,
    )
    tool_doc = build_tool_specifications_document(
        workflow=res.workflow,
        graph=res.graph,
        tool_specs=tool_specs,
    )
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf_tool:
        tmp_tool_path = Path(tf_tool.name)
    try:
        generate_tool_specifications_excel(tool_doc, tmp_tool_path)
        tool_spec_bytes = tmp_tool_path.read_bytes()
    finally:
        if tmp_tool_path.exists():
            tmp_tool_path.unlink()

    # 7. STTM XLSX
    sttm_doc = res.sttm or extract_sttm(res.workflow, res.graph, res.business_summary)
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf_xlsx:
        tmp_xlsx_path = Path(tf_xlsx.name)
    try:
        generate_sttm_excel(sttm_doc, tmp_xlsx_path)
        sttm_bytes = tmp_xlsx_path.read_bytes()
    finally:
        if tmp_xlsx_path.exists():
            tmp_xlsx_path.unlink()

    # Build in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}/workflow.json", json_bytes)
        zf.writestr(f"{base_name}/workflow.py", py_bytes)
        zf.writestr(f"{base_name}/workflow.svg", svg_bytes)
        zf.writestr(f"{base_name}/{base_name}_Business_Report.docx", biz_docx_bytes)
        zf.writestr(f"{base_name}/{base_name}_Tool_Specifications.xlsx", tool_spec_bytes)
        zf.writestr(f"{base_name}/{base_name}_STTM.xlsx", sttm_bytes)
        zf.writestr(f"{base_name}/diagnostics.json", diags_bytes)

    zip_bytes = zip_buffer.getvalue()
    zip_filename = f"{base_name}_bundle.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
