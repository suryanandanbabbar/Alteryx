"""Tests for SupportLevel capabilities across tool tiers."""

import pytest
from awa.tools import get_tool_catalog
from awa.model.diagnostic import SupportLevel


class TestSupportLevels:
    """Validate distribution and classification of support levels."""

    def test_full_support_tools(self):
        catalog = get_tool_catalog()
        full_tools = catalog.get_by_support_level(SupportLevel.FULL)
        names = {t.display_name for t in full_tools}
        assert "Input Data" in names
        assert "Output Data" in names
        assert "Filter" in names
        assert "Formula" in names
        assert "Select" in names
        assert "Sort" in names
        assert "Unique" in names
        assert "Join" in names
        assert "Union" in names
        assert "Summarize" in names
        assert "Transpose" in names
        assert "Cross Tab" in names
        assert "Sample" in names
        assert "Record ID" in names

    def test_pass_through_tools(self):
        catalog = get_tool_catalog()
        pass_through = catalog.get_by_support_level(SupportLevel.PASS_THROUGH)
        names = {t.display_name for t in pass_through}
        assert "Browse" in names
        assert "Block Until Done" in names
        assert "Detour End" in names
        assert "Message" in names

    def test_documentation_only_tools(self):
        catalog = get_tool_catalog()
        doc_tools = catalog.get_by_support_level(SupportLevel.DOCUMENTATION_ONLY)
        names = {t.display_name for t in doc_tools}
        assert "Comment" in names
        assert "Tool Container" in names
        assert "Layout" in names
        assert "Render" in names
        assert "Table" in names

    def test_external_execution_tools(self):
        catalog = get_tool_catalog()
        ext_tools = catalog.get_by_support_level(SupportLevel.EXTERNAL_EXECUTION)
        names = {t.display_name for t in ext_tools}
        assert "Python" in names
        assert "R" in names
        assert "Run Command" in names
        assert "Download" in names
        assert "Connect In-DB" in names
        assert "Amazon S3 Download" in names
        assert "Salesforce Input" in names
