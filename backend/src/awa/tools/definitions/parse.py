"""Parse category tool definitions (Tools 33-36)."""

from __future__ import annotations

from awa.model.diagnostic import SupportLevel
from awa.tools.categories import ToolCategory
from awa.tools.definition import ToolDefinition

PARSE_TOOLS: tuple[ToolDefinition, ...] = (
    # 33. DateTime
    ToolDefinition(
        xml_name="AlteryxBasePluginsGui.DateTime.DateTime",
        display_name="DateTime",
        category=ToolCategory.PARSE,
        support_level=SupportLevel.FULL,
        alters_data=True,
        is_blocking=False,
        is_macro=False,
        has_python_translation=True,
        translator_name="DateTimeTranslator",
        parser_name=None,
        input_anchors=("Input",),
        output_anchors=("Output",),
        aliases=("DateTime",),
        description="Converts datetime data between standardized string representations and native date/time formats.",
        visual_category="datetime",
    ),
    # 34. RegEx
    ToolDefinition(
        xml_name="AlteryxBasePluginsGui.RegEx.RegEx",
        display_name="RegEx",
        category=ToolCategory.PARSE,
        support_level=SupportLevel.FULL,
        alters_data=True,
        is_blocking=False,
        is_macro=False,
        has_python_translation=True,
        translator_name="RegExTranslator",
        parser_name=None,
        input_anchors=("Input",),
        output_anchors=("Output",),
        aliases=("RegEx", "Regex"),
        description="Parses, matches, replaces, or tokenizes string columns using regular expressions.",
        visual_category="regex",
    ),
    # 35. Text To Columns
    ToolDefinition(
        xml_name="AlteryxBasePluginsGui.TextToColumns.TextToColumns",
        display_name="Text To Columns",
        category=ToolCategory.PARSE,
        support_level=SupportLevel.FULL,
        alters_data=True,
        is_blocking=False,
        is_macro=False,
        has_python_translation=True,
        translator_name="TextToColumnsTranslator",
        parser_name=None,
        input_anchors=("Input",),
        output_anchors=("Output",),
        aliases=("TextToColumns",),
        description="Splits a single text column into multiple columns or rows using specified delimiters.",
        visual_category="regex",
    ),
    # 36. XML Parse
    ToolDefinition(
        xml_name="AlteryxBasePluginsGui.XMLParse.XMLParse",
        display_name="XML Parse",
        category=ToolCategory.PARSE,
        support_level=SupportLevel.PARTIAL,
        alters_data=True,
        is_blocking=False,
        is_macro=False,
        has_python_translation=False,
        translator_name=None,
        parser_name=None,
        input_anchors=("Input",),
        output_anchors=("Output",),
        aliases=("XMLParse", "XmlParse"),
        description="Extracts elements, attributes, and text values from XML formatted string columns.",
        visual_category="regex",
    ),
)
