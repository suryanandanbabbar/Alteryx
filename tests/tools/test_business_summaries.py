"""Tests for canonical business summaries and single summary lookup service."""

from pathlib import Path
import pytest

from awa.tools.definitions import ALL_TOOLS
from awa.tools.catalog import get_tool_catalog, get_tool_summary, DEFAULT_CUSTOM_TOOL_SUMMARY


class TestBusinessSummaries:
    """Validate completeness and correctness of tool business summaries."""

    def test_all_100_tools_have_non_empty_business_summaries(self):
        """Every registered tool must have a descriptive, non-empty business summary."""
        assert len(ALL_TOOLS) == 100
        for tool in ALL_TOOLS:
            assert tool.description, f"Tool '{tool.display_name}' ({tool.xml_name}) missing summary"
            assert len(tool.description.strip()) > 10
            # Must avoid internal support classification labels in business description
            forbidden = ["FULL", "PARTIAL", "PASS_THROUGH", "EXTERNAL_EXECUTION", "UNSUPPORTED"]
            for term in forbidden:
                assert term not in tool.description, f"Support tag {term} found in description for {tool.display_name}"

    def test_canonical_xml_lookup(self):
        """Canonical XML names resolve to their business summary."""
        summary = get_tool_summary("AlteryxBasePluginsGui.Filter.Filter")
        assert "Splits incoming" in summary or "True and False" in summary

        summary_db = get_tool_summary("AlteryxBasePluginsGui.DbFileInput.DbFileInput")
        assert "Reads records" in summary_db or "files" in summary_db

    def test_short_name_and_display_name_lookup(self):
        """Short names and display names resolve to the same summary."""
        summary_short = get_tool_summary("Filter")
        summary_disp = get_tool_summary("Formula")
        assert summary_short
        assert summary_disp
        assert summary_short != DEFAULT_CUSTOM_TOOL_SUMMARY
        assert summary_disp != DEFAULT_CUSTOM_TOOL_SUMMARY

    def test_alias_lookup(self):
        """Macro aliases and plugin aliases resolve correctly."""
        summary_cleanse = get_tool_summary("Cleanse.yxmc")
        assert "Cleanses" in summary_cleanse or "whitespace" in summary_cleanse

        summary_dt = get_tool_summary("DateTimeNow.yxmc")
        assert "date and time" in summary_dt or "current" in summary_dt

    def test_unknown_custom_tool_fallback(self):
        """Unknown or unregistered tools receive the safe neutral fallback."""
        summary_unknown = get_tool_summary("CustomCompanyPlugin.SecretTool.SecretTool")
        assert summary_unknown == DEFAULT_CUSTOM_TOOL_SUMMARY
        assert "Support Level" not in summary_unknown
        assert "UNSUPPORTED" not in summary_unknown

    def test_matrix_markdown_table_integrity(self):
        """Ensure docs/tool-support-matrix.md exists and contains 100 rows with summaries."""
        matrix_path = Path("docs/tool-support-matrix.md")
        assert matrix_path.exists(), "docs/tool-support-matrix.md must exist"

        content = matrix_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip().startswith("|")]
        # Exclude header and separator rows
        data_rows = [l for l in lines if not l.startswith("| #") and not l.startswith("|---")]
        assert len(data_rows) == 100, f"Expected 100 tools in matrix, found {len(data_rows)}"
        for row in data_rows:
            cols = [c.strip() for c in row.split("|")]
            # Format: | # | Category | Tool Name | XML Tool Name | Business Summary | ...
            assert len(cols) >= 6
            summary = cols[5]
            assert len(summary) > 5, f"Empty or too short summary in row: {row}"
