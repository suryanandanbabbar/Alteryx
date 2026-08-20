"""Tests for configuration code humanizer and resolver."""

from pathlib import Path
import pytest

from awa.tools.humanizer import (
    resolve_file_format,
    humanize_config_key,
    humanize_config_value,
    humanize_tool_configuration,
    ALTERYX_FILE_FORMAT_MAP,
)
from awa.analysis.workflow_analyzer import analyze_canonical
from backend.app.services.analyzer import to_diagram_dto


class TestHumanizer:
    """Verify that machine-oriented Alteryx codes and configuration dictionaries are humanized."""

    def test_resolve_file_format_codes(self):
        """Verify standard Alteryx file format enumeration codes."""
        assert resolve_file_format(19) == "Alteryx Database (.yxdb)"
        assert resolve_file_format("19") == "Alteryx Database (.yxdb)"
        assert resolve_file_format(0) == "CSV / Delimited (.csv)"
        assert resolve_file_format("0") == "CSV / Delimited (.csv)"
        assert resolve_file_format(8) == "Microsoft Excel (.xlsx / .xlsm)"
        assert resolve_file_format(28) == "Tableau Hyper Data Extract (.hyper)"
        assert resolve_file_format(36) == "Apache Parquet (.parquet)"
        assert resolve_file_format(54) == "JSON Data (.json)"
        assert resolve_file_format(".yxdb") == "Alteryx Database (.yxdb)"
        assert resolve_file_format(None) == "Auto-Detect / Default"

    def test_humanize_config_keys(self):
        """Verify configuration key humanization."""
        assert humanize_config_key("file_format") == "File Format"
        assert humanize_config_key("file_path") == "File Path"
        assert humanize_config_key("record_limit") == "Record Limit"
        assert humanize_config_key("join_by_pos") == "Join Method"
        assert humanize_config_key("by_name_or_pos") == "Union Alignment Mode"
        assert humanize_config_key("custom_property_name") == "Custom Property Name"

    def test_humanize_config_values(self):
        """Verify configuration value translation."""
        assert humanize_config_value("file_format", 19) == "Alteryx Database (.yxdb)"
        assert humanize_config_value("file_format", "19") == "Alteryx Database (.yxdb)"
        assert humanize_config_value("record_limit", "0") == "All records (No limit)"
        assert humanize_config_value("record_limit", "500") == "500 records"
        assert humanize_config_value("join_by_pos", True) == "Join by record position"
        assert humanize_config_value("join_by_pos", False) == "Join by matching specific key fields"
        assert humanize_config_value("search_subdirs", True) == "Search subdirectories (Recursive)"
        assert humanize_config_value("search_subdirs", False) == "Top-level directory only"
        assert humanize_config_value("by_name_or_pos", "ByName") == "Align by column name"

    def test_humanize_complex_field_structures(self):
        """Verify formula, summarize, select, and sort list structures."""
        formulas = [{"field": "Tax", "expression": "[Total] * 0.08", "type": "Double"}]
        assert humanize_config_value("formula_fields", formulas) == "Tax : Double = [Total] * 0.08"

        summaries = [{"field": "Revenue", "action": "Sum", "rename": "Total_Revenue"}]
        assert humanize_config_value("summarize_fields", summaries) == "Revenue (Sum → Total_Revenue)"

        selects = [{"field": "OldName", "selected": True, "rename": "NewName", "type": "Int64"}]
        assert humanize_config_value("select_fields", selects) == "OldName → NewName, Int64"

        joins = [{"left": "CustomerID", "right": "Cust_ID"}]
        assert humanize_config_value("join_fields", joins) == "CustomerID = Cust_ID"

    def test_humanize_tool_configuration_dict(self):
        """Verify entire tool configuration dictionary transformation."""
        raw_config = {
            "file_path": "\\\\server\\data\\orders.yxdb",
            "file_format": "19",
            "record_limit": "0",
            "search_subdirs": "True",
        }
        humanized = humanize_tool_configuration("DbFileInput", raw_config)
        assert humanized["File Path"] == "\\\\server\\data\\orders.yxdb"
        assert humanized["File Format"] == "Alteryx Database (.yxdb)"
        assert humanized["Record Limit"] == "All records (No limit)"
        assert humanized["Search Subdirectories"] == "Search subdirectories (Recursive)"

    def test_simple_filter_dto_configuration_humanized(self):
        """Verify that NodeDTO in diagram endpoint contains humanized configuration."""
        canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
        diagram_dto = to_diagram_dto(canonical)
        tool1 = next(n for n in diagram_dto.nodes if n.tool_id == 1)
        assert tool1.configuration.get("File Format") == "Alteryx Database (.yxdb)"
        assert "19" != tool1.configuration.get("File Format")
