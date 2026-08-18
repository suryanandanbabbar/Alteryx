"""Tests for unknown and custom tool graceful fallback handling."""

import pytest
from awa.tools import create_fallback_tool_definition, resolve_tool_definition
from awa.model.diagnostic import SupportLevel
from awa.model.tool import Tool, ToolConfiguration
from awa.translators.registry import get_translator
from awa.model.workflow import Workflow, WorkflowMetadata


class TestUnknownTools:
    """Validate that unknown tools are safely handled without throwing exceptions."""

    def test_fallback_definition_properties(self):
        fallback = create_fallback_tool_definition("Vendor.CustomTransformer.SpecialTool")
        assert fallback.xml_name == "Vendor.CustomTransformer.SpecialTool"
        assert fallback.display_name == "SpecialTool"
        assert fallback.support_level == SupportLevel.UNSUPPORTED
        assert fallback.alters_data is True
        assert fallback.has_python_translation is False

    def test_unknown_tool_translator_execution(self):
        tool = Tool(
            tool_id=999,
            plugin="Vendor.CustomTransformer.SpecialTool",
            tool_type="SpecialTool",
            name="My Custom Step",
            position=None,
            configuration=ToolConfiguration(raw_xml="<Configuration><SecretKey>123</SecretKey></Configuration>"),
        )
        wf = Workflow(
            metadata=WorkflowMetadata(name="TestWF", version="2024.1"),
            tools={999: tool},
            connections=[],
        )

        translator = get_translator(tool)
        res = translator.translate(tool, ["df_input"], wf)

        assert res.tool_id == 999
        assert res.support_level == SupportLevel.UNSUPPORTED
        assert "raise NotImplementedError" in res.python_code
        assert len(res.diagnostics) == 1
        assert res.diagnostics[0].category == "unsupported_tool"
