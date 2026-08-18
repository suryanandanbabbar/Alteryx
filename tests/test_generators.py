"""Tests for DOCX and SVG output generators."""

from pathlib import Path
import docx
import pytest

from backend.src.awa.parser.xml_parser import parse_workflow
from backend.src.awa.graph.builder import build_graph, execution_order, build_input_map
from backend.src.awa.graph.dag_layouter import compute_dag_layout
from backend.src.awa.graph.lineage import compute_lineage_paths
from backend.src.awa.translators.registry import get_translator
import backend.src.awa.translators  # register translators
from backend.src.awa.generators.doc_builder import build_document_model
from backend.src.awa.generators.docx_generator import generate_docx
from backend.src.awa.generators.svg_generator import generate_svg


def test_docx_generation(tmp_path: Path):
    wf = parse_workflow("fixtures/joins/join_workflow.yxmd")
    g = build_graph(wf)
    order = execution_order(g)
    input_map = build_input_map(wf)

    translations = {}
    for tid in order:
        tool = wf.tools[tid]
        tr = get_translator(tool)
        translations[tid] = tr.translate(tool, input_map.get(tid, []), wf)

    layout = compute_dag_layout(g, wf, order)
    lineage = compute_lineage_paths(wf, g)

    doc_model = build_document_model(wf, order, translations, layout, lineage)
    assert doc_model.title.startswith("Alteryx Workflow Documentation")
    assert len(doc_model.nodes) == 6
    assert len(doc_model.execution_order) == 6

    docx_path = tmp_path / "workflow.docx"
    generate_docx(doc_model, docx_path)

    assert docx_path.exists()
    assert docx_path.stat().st_size > 0

    # Verify python-docx can open and read it
    doc = docx.Document(str(docx_path))
    headings = [p.text for p in doc.paragraphs if p.text.startswith("1.") or p.text.startswith("2.") or p.text.startswith("3.")]
    assert len(headings) >= 3
    assert len(doc.tables) >= 3
