"""Tests for ToolCatalog loading, iteration, and counts."""

import pytest
from awa.tools import get_tool_catalog, ToolCatalog
from awa.tools.categories import ToolCategory
from awa.tools.definitions import ALL_TOOLS


class TestToolCatalog:
    """Test ToolCatalog collection structure and properties."""

    def test_catalog_singleton_count(self):
        catalog = get_tool_catalog()
        assert catalog.primary_tool_count == 100
        assert len(catalog) == 100

    def test_all_tools_tuple_count(self):
        assert len(ALL_TOOLS) == 100

    def test_catalog_iteration(self):
        catalog = get_tool_catalog()
        tools_list = list(catalog)
        assert len(tools_list) == 100

    def test_catalog_categories_coverage(self):
        catalog = get_tool_catalog()
        categories = {t.category for t in catalog}
        # All 11 authoritative categories must be represented
        assert len(categories) == 11
        for cat in ToolCategory:
            assert cat in categories or cat.value in categories

    def test_catalog_category_breakdown(self):
        catalog = get_tool_catalog()
        in_out = catalog.get_by_category(ToolCategory.IN_OUT)
        prep = catalog.get_by_category(ToolCategory.PREPARATION)
        join = catalog.get_by_category(ToolCategory.JOIN)
        parse = catalog.get_by_category(ToolCategory.PARSE)
        transform = catalog.get_by_category(ToolCategory.TRANSFORM)
        dev = catalog.get_by_category(ToolCategory.DEVELOPER)
        doc = catalog.get_by_category(ToolCategory.DOCUMENTATION)
        reporting = catalog.get_by_category(ToolCategory.REPORTING)
        spatial = catalog.get_by_category(ToolCategory.SPATIAL)
        in_db = catalog.get_by_category(ToolCategory.IN_DATABASE)
        connectors = catalog.get_by_category(ToolCategory.CONNECTORS)

        assert len(in_out) == 6
        assert len(prep) == 19
        assert len(join) == 7
        assert len(parse) == 4
        assert len(transform) == 7
        assert len(dev) == 15
        assert len(doc) == 2
        assert len(reporting) == 10
        assert len(spatial) == 14
        assert len(in_db) == 7
        assert len(connectors) == 9
