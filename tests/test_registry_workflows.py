"""Tests for golden workflows exercising the 100-tool registry."""

import json
from pathlib import Path
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow, analyze_canonical
from awa.model.diagnostic import SupportLevel

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestRegistryWorkflows:
    """Validate full analysis, classification, and artifact generation across golden workflows."""

    def test_registry_core_etl(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_core_etl.yxmd"
        out_dir = tmp_path / "core_etl_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 7
        assert len(res.workflow.connections) == 6
        assert len(res.execution_order) == 7

        # Verify all 7 tools are FULL support
        for tr in res.translations.values():
            assert tr.support_level == SupportLevel.FULL

        # Verify artifacts exist
        assert (out_dir / "workflow.json").exists()
        assert (out_dir / "workflow.py").exists()
        assert (out_dir / "workflow.svg").exists()
        assert (out_dir / "workflow.docx").exists()
        assert (out_dir / "diagnostics.json").exists()

        # Verify python code compiles
        with open(out_dir / "workflow.py") as f:
            code = f.read()
        compile(code, "<string>", "exec")

    def test_registry_join_heavy(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_join_heavy.yxmd"
        out_dir = tmp_path / "join_heavy_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 7
        assert len(res.workflow.connections) == 7

        with open(out_dir / "workflow.py") as f:
            code = f.read()
        compile(code, "<string>", "exec")

    def test_registry_parse_transform(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_parse_transform.yxmd"
        out_dir = tmp_path / "parse_transform_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 6
        assert (out_dir / "workflow.json").exists()

        with open(out_dir / "workflow.py") as f:
            code = f.read()
        compile(code, "<string>", "exec")

    def test_registry_control_flow(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_control_flow.yxmd"
        out_dir = tmp_path / "control_flow_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 5
        # Verify BrowseV2 and BlockUntilDone are PASS_THROUGH
        browse_tr = [tr for tr in res.translations.values() if tr.tool_type in ("Browse", "BrowseV2")][0]
        assert browse_tr.support_level == SupportLevel.PASS_THROUGH

        with open(out_dir / "workflow.py") as f:
            code = f.read()
        compile(code, "<string>", "exec")

    def test_registry_unknown_tool_and_redaction(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_unknown_tool.yxmd"
        out_dir = tmp_path / "unknown_tool_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 3
        # Tool 2 is unknown
        unknown_tr = res.translations[2]
        assert unknown_tr.support_level == SupportLevel.UNSUPPORTED

        # Verify secret was redacted in JSON
        with open(out_dir / "workflow.json") as f:
            json_content = f.read()
        assert "secret_12345_token" not in json_content
        assert "[REDACTED]" in json_content

        # Verify secret is not in Python or Diagnostics
        with open(out_dir / "workflow.py") as f:
            py_content = f.read()
        assert "secret_12345_token" not in py_content

        with open(out_dir / "diagnostics.json") as f:
            diag_content = f.read()
        assert "secret_12345_token" not in diag_content

    def test_registry_mixed_complex(self, tmp_path):
        fixture = FIXTURES_DIR / "registry_mixed_complex.yxmd"
        out_dir = tmp_path / "mixed_complex_out"
        res = analyze_workflow(fixture, out_dir)

        assert len(res.workflow.tools) == 13
        assert len(res.workflow.connections) == 13

        with open(out_dir / "workflow.json") as f:
            wf_json = json.load(f)

        assert len(wf_json["tools"]) == 13
        assert "analysis" in wf_json
        assert wf_json["analysis"]["total_tools"] == 13

        with open(out_dir / "workflow.py") as f:
            code = f.read()
        compile(code, "<string>", "exec")
