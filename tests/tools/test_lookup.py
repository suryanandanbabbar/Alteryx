"""Tests for catalog lookup APIs by XML name, alias, and display name."""

import pytest
from awa.tools import (
    get_tool_catalog,
    get_tool_definition,
    get_tool_definition_by_display_name,
    resolve_tool_definition,
    is_known_tool,
)
from awa.model.diagnostic import SupportLevel


class TestToolLookup:
    """Test lookup mechanisms."""

    def test_lookup_by_exact_xml_name(self):
        tool = get_tool_definition("AlteryxBasePluginsGui.DbFileInput.DbFileInput")
        assert tool is not None
        assert tool.display_name == "Input Data"

    def test_lookup_by_short_name(self):
        tool = get_tool_definition("DbFileInput")
        assert tool is not None
        assert tool.display_name == "Input Data"

    def test_lookup_by_alias(self):
        tool = get_tool_definition("InputData")
        assert tool is not None
        assert tool.display_name == "Input Data"

    def test_lookup_by_display_name(self):
        tool = get_tool_definition_by_display_name("Filter")
        assert tool is not None
        assert tool.xml_name == "AlteryxBasePluginsGui.Filter.Filter"

    def test_lookup_by_display_name_case_insensitive(self):
        tool = get_tool_definition_by_display_name("data cleansing")
        assert tool is not None
        assert tool.display_name == "Data Cleansing"

    def test_is_known_tool(self):
        assert is_known_tool("AlteryxBasePluginsGui.Filter.Filter") is True
        assert is_known_tool("Filter") is True
        assert is_known_tool("SomeNonExistentPlugin.FakeTool") is False

    def test_resolve_known_tool(self):
        tool = resolve_tool_definition("AlteryxBasePluginsGui.Sort.Sort")
        assert tool.display_name == "Sort"
        assert tool.support_level == SupportLevel.FULL

    def test_resolve_unknown_tool_returns_fallback(self):
        tool = resolve_tool_definition("CustomCompany.SpecialProcessingTool")
        assert tool is not None
        assert tool.display_name == "SpecialProcessingTool"
        assert tool.support_level == SupportLevel.UNSUPPORTED
        assert tool.has_python_translation is False
