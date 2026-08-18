"""Download endpoints for generating and streaming export artifacts."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from backend.src.awa.generators.svg_generator import generate_svg
from backend.src.awa.generators.docx_generator import generate_docx
from backend.src.awa.generators.doc_builder import build_document_model
from backend.src.awa.generators.python_generator import generate_python_code
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


@router.get("/{analysis_id}/docx")
def download_docx(analysis_id: str):
    """Download the Word documentation (.docx) for the workflow."""
    res = _get_result_or_404(analysis_id)
    doc_model = build_document_model(
        res.workflow,
        res.execution_order,
        res.translations,
        res.dag_layout,
        res.lineage_paths,
    )
    svg_str = generate_svg(res.dag_layout)

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        tmp_path = Path(tf.name)

    try:
        generate_docx(doc_model, tmp_path, svg_content=svg_str)
        docx_bytes = tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    filename = f"{res.workflow.metadata.name or 'workflow'}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
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
    """Download the executable Python/pandas pipeline script."""
    res = _get_result_or_404(analysis_id)
    code, _, _ = generate_python_code(
        res.workflow, res.execution_order, res.translations, res.consumed_anchors
    )
    py_bytes = code.encode("utf-8")
    filename = f"{res.workflow.metadata.name or 'workflow'}.py"

    return Response(
        content=py_bytes,
        media_type="text/x-python",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/svg")
def download_svg(analysis_id: str):
    """Download the standalone DAG vector diagram (.svg)."""
    res = _get_result_or_404(analysis_id)
    svg_str = generate_svg(res.dag_layout)
    svg_bytes = svg_str.encode("utf-8")
    filename = f"{res.workflow.metadata.name or 'workflow'}_dag.svg"

    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{analysis_id}/zip")
def download_zip(analysis_id: str):
    """Download a single ZIP archive containing all generated artifacts."""
    res = _get_result_or_404(analysis_id)
    base_name = res.workflow.metadata.name or "workflow"

    # 1. JSON
    json_bytes = json.dumps(res.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")

    # 2. Python
    code, _, _ = generate_python_code(
        res.workflow, res.execution_order, res.translations, res.consumed_anchors
    )
    py_bytes = code.encode("utf-8")

    # 3. SVG
    svg_str = generate_svg(res.dag_layout)
    svg_bytes = svg_str.encode("utf-8")

    # 4. Diagnostics JSON
    diags_data = {
        "diagnostics": [d.to_dict() for d in res.diagnostics],
        "support_summary": res.metrics.support_summary,
    }
    diags_bytes = json.dumps(diags_data, indent=2, ensure_ascii=False).encode("utf-8")

    # 5. DOCX
    doc_model = build_document_model(
        res.workflow,
        res.execution_order,
        res.translations,
        res.dag_layout,
        res.lineage_paths,
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tf:
        tmp_path = Path(tf.name)
    try:
        generate_docx(doc_model, tmp_path, svg_content=svg_str)
        docx_bytes = tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    # Build in-memory ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}/workflow.json", json_bytes)
        zf.writestr(f"{base_name}/workflow.py", py_bytes)
        zf.writestr(f"{base_name}/workflow.svg", svg_bytes)
        zf.writestr(f"{base_name}/workflow.docx", docx_bytes)
        zf.writestr(f"{base_name}/diagnostics.json", diags_bytes)

    zip_bytes = zip_buffer.getvalue()
    zip_filename = f"{base_name}_bundle.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )
