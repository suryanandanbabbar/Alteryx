"""Regression tests for the 5 verified defects.

1. Python trace total_lines exact match
2. DOCX embedded DAG image verification
3. External dependency diagnostics for UNC/unresolved paths
4. Canonical JSON completeness (EngineSettings preservation)
5. Execution equivalence vs static validation distinction
"""

import json
from pathlib import Path
import zipfile
import pytest

from backend.src.awa.analysis.workflow_analyzer import analyze_canonical, analyze_workflow
from backend.src.awa.generators.python_generator import generate_python_code
from backend.src.awa.model.diagnostic import DiagnosticLevel, SupportLevel


def test_defect1_python_trace_total_lines_exact_match():
    canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    code, trace_map, _ = generate_python_code(
        canonical.workflow,
        canonical.execution_order,
        canonical.translations,
        canonical.consumed_anchors,
    )
    code_lines = code.splitlines()
    # Must match exactly
    assert trace_map.total_lines == len(code_lines)
    # Trace entries must fit within total_lines
    for entry in trace_map.entries:
        assert 1 <= entry.start_line <= entry.end_line <= trace_map.total_lines


def test_defect2_docx_contains_embedded_dag_image(tmp_path: Path):
    out_dir = tmp_path / "simple_filter_out"
    analyze_workflow("fixtures/basic/simple_filter.yxmd", out_dir)
    docx_file = out_dir / "workflow.docx"
    assert docx_file.exists()

    with zipfile.ZipFile(docx_file, "r") as zf:
        media_files = [f for f in zf.namelist() if f.startswith("word/media/")]
        assert len(media_files) >= 1, "Expected word/media/image in DOCX package"


def test_defect3_external_dependency_diagnostic():
    canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    
    # DbFileInput translation should be SUPPORTED
    tool1_tr = canonical.translations[1]
    assert tool1_tr.support_level == SupportLevel.SUPPORTED

    # But should contain an external_dependency diagnostic
    ext_diags = [
        d for d in tool1_tr.diagnostics
        if d.category == "external_dependency"
    ]
    assert len(ext_diags) >= 1
    assert "\\\\server\\data\\customers.xlsx" in ext_diags[0].message or "customers.xlsx" in ext_diags[0].message

    # Total diagnostics in canonical result must contain external_dependency
    all_ext_diags = [d for d in canonical.diagnostics if d.category == "external_dependency"]
    assert len(all_ext_diags) >= 1


def test_defect4_canonical_json_preserves_engine_settings():
    canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    tool1 = canonical.workflow.tools[1]
    
    assert hasattr(tool1, "engine_settings")
    assert tool1.engine_settings.get("EngineDll") == "AlteryxBasePluginsEngine.dll"
    assert tool1.engine_settings.get("EngineDllEntryPoint") == "AlteryxDbFileInput"

    d = tool1.to_dict()
    assert "engine_settings" in d
    assert d["engine_settings"]["EngineDll"] == "AlteryxBasePluginsEngine.dll"


def test_defect5_execution_equivalence_distinction():
    canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    
    # Check that unresolved dependencies are flagged as unresolved
    unresolved_deps = [dep for dep in canonical.workflow.dependencies if not dep.resolved]
    assert len(unresolved_deps) >= 1
    assert unresolved_deps[0].reference == r"\\server\data\customers.xlsx"
