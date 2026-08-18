"""Documentation category tool definitions (Tools 59-60)."""

from __future__ import annotations

from awa.model.diagnostic import SupportLevel
from awa.tools.categories import ToolCategory
from awa.tools.definition import ToolDefinition

DOCUMENTATION_TOOLS: tuple[ToolDefinition, ...] = (
    # 59. Comment
    ToolDefinition(
        xml_name="AlteryxGuiToolkit.TextBox.TextBox",
        display_name="Comment",
        category=ToolCategory.DOCUMENTATION,
        support_level=SupportLevel.DOCUMENTATION_ONLY,
        alters_data=False,
        is_blocking=False,
        is_macro=False,
        has_python_translation=False,
        translator_name="DocumentationTranslator",
        parser_name=None,
        input_anchors=(),
        output_anchors=(),
        aliases=("TextBox", "Comment"),
        description="Places free-form documentation, markdown notes, and visual annotation boxes on the workflow canvas.",
        visual_category="documentation",
    ),
    # 60. Tool Container
    ToolDefinition(
        xml_name="AlteryxGuiToolkit.ToolContainer.ToolContainer",
        display_name="Tool Container",
        category=ToolCategory.DOCUMENTATION,
        support_level=SupportLevel.DOCUMENTATION_ONLY,
        alters_data=False,
        is_blocking=False,
        is_macro=False,
        has_python_translation=False,
        translator_name="DocumentationTranslator",
        parser_name=None,
        input_anchors=(),
        output_anchors=(),
        aliases=("ToolContainer",),
        description="Organizes and visually isolates a group of workflow tools into a collapsable, toggleable boundary box.",
        visual_category="documentation",
    ),
)
