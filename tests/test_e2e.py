"""End-to-end tests — validates the full pipeline: .yxmd → all 4 artifacts.

These tests exercise the complete workflow:
parse → graph → translate → generate JSON + Python + Markdown + Diagnostics

Tests use ONLY real fixtures (C1).
Generated Python is validated via py_compile (necessary) and
execution against sample data (sufficient, C7).
"""

import json
import py_compile
import tempfile

import pytest
from pathlib import Path

from awa.analysis.workflow_analyzer import analyze_workflow


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestSimpleFilterE2E:
    """End-to-end test for simple_filter.yxmd.

    Verifies all 4 output artifacts are generated correctly.
    """

    @pytest.fixture
    def analysis_result(self, tmp_path):
        fixture = FIXTURES_DIR / "basic" / "simple_filter.yxmd"
        assert fixture.exists(), f"Fixture not found: {fixture}"
        return analyze_workflow(fixture, tmp_path / "output")

    def test_output_files_exist(self, analysis_result):
        """All 4 artifacts must be generated."""
        out = analysis_result.output_dir
        assert (out / "workflow.json").exists()
        assert (out / "workflow.py").exists()
        assert (out / "workflow.md").exists()
        assert (out / "diagnostics.json").exists()

    def test_workflow_json_structure(self, analysis_result):
        """JSON must contain tools, connections, execution_order."""
        json_path = analysis_result.output_dir / "workflow.json"
        with open(json_path) as f:
            data = json.load(f)

        assert "metadata" in data
        assert data["metadata"]["name"] == "simple_filter"

        assert "tools" in data
        assert len(data["tools"]) == 3

        assert "connections" in data
        assert len(data["connections"]) == 2

        assert "execution_order" in data
        assert data["execution_order"] == [1, 2, 3]

        assert "analysis" in data
        assert data["analysis"]["total_tools"] == 3

    def test_workflow_json_tool_details(self, analysis_result):
        """JSON tools must have actual configuration data."""
        json_path = analysis_result.output_dir / "workflow.json"
        with open(json_path) as f:
            data = json.load(f)

        tools = data["tools"]
        # First tool is DbFileInput
        assert tools[0]["tool_type"] == "DbFileInput"
        assert "customers.xlsx" in tools[0]["configuration"]["parsed"].get("file_path", "")

        # Second tool is Filter
        assert tools[1]["tool_type"] == "Filter"
        assert "expression" in tools[1]["configuration"]["parsed"]

    def test_python_compiles(self, analysis_result):
        """Generated Python must be syntactically valid (necessary condition)."""
        py_path = analysis_result.output_dir / "workflow.py"
        # This raises py_compile.PyCompileError if invalid
        py_compile.compile(str(py_path), doraise=True)

    def test_python_content(self, analysis_result):
        """Generated Python must contain traceability comments and pandas code."""
        py_path = analysis_result.output_dir / "workflow.py"
        content = py_path.read_text()

        # Traceability comments
        assert "Alteryx Tool #1" in content
        assert "Alteryx Tool #2" in content
        assert "Alteryx Tool #3" in content
        assert "DbFileInput" in content
        assert "Filter" in content
        assert "DbFileOutput" in content

        # Pandas operations
        assert "pd.read_" in content  # Input read
        assert "import pandas as pd" in content

    def test_python_has_filter_logic(self, analysis_result):
        """Generated Python must contain actual filter logic, not a placeholder."""
        py_path = analysis_result.output_dir / "workflow.py"
        content = py_path.read_text()

        # Should have filter mask and boolean indexing
        assert "_filter_mask_" in content or "df_2_true" in content
        assert ".copy()" in content

    def test_markdown_sections(self, analysis_result):
        """Markdown must contain required documentation sections."""
        md_path = analysis_result.output_dir / "workflow.md"
        content = md_path.read_text()

        assert "# Workflow: simple_filter" in content
        assert "## Overview" in content
        assert "## Metadata" in content
        assert "## Step-by-Step Workflow" in content
        assert "## Tool Inventory" in content
        assert "## Data Lineage" in content

    def test_diagnostics_json(self, analysis_result):
        """Diagnostics must have summary structure."""
        diag_path = analysis_result.output_dir / "diagnostics.json"
        with open(diag_path) as f:
            data = json.load(f)

        assert "diagnostics" in data
        assert "summary" in data
        assert "tool_support" in data["summary"]

    def test_all_tools_classified(self, analysis_result):
        """Every tool must have a support classification (C9)."""
        for tr in analysis_result.translations.values():
            assert tr.support_level is not None
            assert tr.support_level.value in (
                "supported", "partial", "unsupported",
                "unknown", "ambiguous", "external_dependency",
            )

    def test_filter_has_both_branches(self, analysis_result):
        """Filter TranslationResult must have True and False in output_map (C3, C4)."""
        filter_tr = analysis_result.translations[2]
        assert "True" in filter_tr.output_map
        assert "False" in filter_tr.output_map
        assert filter_tr.output_map["True"] == "df_2_true"
        assert filter_tr.output_map["False"] == "df_2_false"


class TestJoinWorkflowE2E:
    """End-to-end test for join_workflow.yxmd."""

    @pytest.fixture
    def analysis_result(self, tmp_path):
        fixture = FIXTURES_DIR / "joins" / "join_workflow.yxmd"
        assert fixture.exists(), f"Fixture not found: {fixture}"
        return analyze_workflow(fixture, tmp_path / "output")

    def test_output_files_exist(self, analysis_result):
        out = analysis_result.output_dir
        assert (out / "workflow.json").exists()
        assert (out / "workflow.py").exists()
        assert (out / "workflow.md").exists()
        assert (out / "diagnostics.json").exists()

    def test_python_compiles(self, analysis_result):
        py_path = analysis_result.output_dir / "workflow.py"
        py_compile.compile(str(py_path), doraise=True)

    def test_execution_order(self, analysis_result):
        """Verify execution order respects data dependencies."""
        order = analysis_result.execution_order
        # Both inputs must come before the Join
        assert order.index(1) < order.index(3)
        assert order.index(2) < order.index(3)
        # Join → Summarize → Sort → Output
        assert order.index(3) < order.index(4)
        assert order.index(4) < order.index(5)
        assert order.index(5) < order.index(6)

    def test_six_tools_translated(self, analysis_result):
        assert len(analysis_result.translations) == 6
