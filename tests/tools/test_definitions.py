"""Tests for individual ToolDefinition structure and serialization."""

import pytest
from awa.tools import get_tool_catalog, ToolDefinition
from awa.model.diagnostic import SupportLevel
from awa.tools.categories import ToolCategory


class TestToolDefinitions:
    """Validate properties and behavior of ToolDefinition instances."""

    def test_filter_definition(self):
        catalog = get_tool_catalog()
        defn = catalog.get("AlteryxBasePluginsGui.Filter.Filter")
        assert defn is not None
        assert defn.display_name == "Filter"
        assert defn.category == ToolCategory.PREPARATION
        assert defn.support_level == SupportLevel.FULL
        assert defn.has_python_translation is True
        assert defn.translator_name == "FilterTranslator"
        assert defn.input_anchors == ("Input",)
        assert defn.output_anchors == ("True", "False")

    def test_browse_definition(self):
        catalog = get_tool_catalog()
        defn = catalog.get("AlteryxBasePluginsGui.BrowseV2.BrowseV2")
        assert defn is not None
        assert defn.display_name == "Browse"
        assert defn.category == ToolCategory.IN_OUT
        assert defn.support_level == SupportLevel.PASS_THROUGH
        assert defn.has_python_translation is False
        assert defn.alters_data is False

    def test_join_definition(self):
        catalog = get_tool_catalog()
        defn = catalog.get("AlteryxBasePluginsGui.Join.Join")
        assert defn is not None
        assert defn.display_name == "Join"
        assert defn.category == ToolCategory.JOIN
        assert defn.support_level == SupportLevel.FULL
        assert defn.input_anchors == ("Left", "Right")
        assert defn.output_anchors == ("Left", "Join", "Right")

    def test_summarize_definition(self):
        catalog = get_tool_catalog()
        defn = catalog.get("AlteryxSpatialPluginsGui.Summarize.Summarize")
        assert defn is not None
        assert defn.display_name == "Summarize"
        assert defn.category == ToolCategory.TRANSFORM
        assert defn.support_level == SupportLevel.FULL
        assert defn.is_blocking is True

    def test_to_dict_serialization(self):
        catalog = get_tool_catalog()
        defn = catalog.get("AlteryxBasePluginsGui.Filter.Filter")
        assert defn is not None
        data = defn.to_dict()
        assert data["xml_name"] == "AlteryxBasePluginsGui.Filter.Filter"
        assert data["display_name"] == "Filter"
        assert data["category"] == "Preparation"
        assert data["support_level"] == "full"
        assert data["has_python_translation"] is True
        assert "capabilities" in data
        assert data["capabilities"]["parsed"] is True
        assert data["capabilities"]["python"] is True
