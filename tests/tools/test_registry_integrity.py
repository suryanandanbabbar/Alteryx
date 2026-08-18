"""Registry integrity tests verifying the 100-tool catalog invariants."""

import pytest
from awa.tools import get_tool_catalog
from awa.model.diagnostic import SupportLevel
from awa.model.tool import Tool, ToolConfiguration
from awa.translators.registry import get_translator
from awa.translators.base import UnsupportedTranslator


class TestRegistryIntegrity:
    """Rigorous structural integrity checks on the 100 curated tools."""

    def test_exactly_100_primary_tools(self):
        catalog = get_tool_catalog()
        assert catalog.primary_tool_count == 100
        assert len(catalog.get_all()) == 100

    def test_no_duplicate_canonical_xml_names(self):
        catalog = get_tool_catalog()
        xml_names = [tool.xml_name for tool in catalog]
        assert len(xml_names) == len(set(xml_names)), "Duplicate XML names detected in catalog"

    def test_every_tool_has_category(self):
        catalog = get_tool_catalog()
        for tool in catalog:
            assert tool.category is not None, f"Tool {tool.display_name} has no category"
            assert len(str(tool.category)) > 0

    def test_every_tool_has_support_classification(self):
        catalog = get_tool_catalog()
        for tool in catalog:
            assert isinstance(tool.support_level, SupportLevel), f"Tool {tool.display_name} has invalid support level {tool.support_level}"

    def test_every_tool_has_description(self):
        catalog = get_tool_catalog()
        for tool in catalog:
            assert tool.description, f"Tool {tool.display_name} is missing a description"

    def test_translator_consistency(self):
        """If tool.has_python_translation is True, translator_name must be present and resolve."""
        catalog = get_tool_catalog()
        for tool_def in catalog:
            if tool_def.has_python_translation:
                assert tool_def.translator_name is not None, f"Tool {tool_def.display_name} claims python translation but has no translator_name"
                mock_tool = Tool(
                    tool_id=1,
                    plugin=tool_def.xml_name,
                    tool_type=tool_def.display_name,
                    name=tool_def.display_name,
                    position=None,
                    configuration=ToolConfiguration(raw_xml="<Configuration/>"),
                )
                translator = get_translator(mock_tool)
                assert not isinstance(translator, UnsupportedTranslator), f"Tool {tool_def.display_name} translator '{tool_def.translator_name}' did not resolve"

    def test_pass_through_and_documentation_resolvers(self):
        """Pass-through and documentation tools must resolve without falling back to UnsupportedTranslator."""
        catalog = get_tool_catalog()
        for tool_def in catalog:
            if tool_def.support_level in (SupportLevel.PASS_THROUGH, SupportLevel.DOCUMENTATION_ONLY):
                mock_tool = Tool(
                    tool_id=1,
                    plugin=tool_def.xml_name,
                    tool_type=tool_def.display_name,
                    name=tool_def.display_name,
                    position=None,
                    configuration=ToolConfiguration(raw_xml="<Configuration/>"),
                )
                translator = get_translator(mock_tool)
                assert not isinstance(translator, UnsupportedTranslator), f"Tool {tool_def.display_name} fell back to UnsupportedTranslator"
