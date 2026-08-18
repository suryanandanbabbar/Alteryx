"""AWA Alteryx Tool Registry package."""

from __future__ import annotations

from awa.tools.categories import ToolCategory, CATEGORY_TO_VISUAL
from awa.tools.capabilities import ToolCapabilities
from awa.tools.definition import ToolDefinition
from awa.tools.catalog import (
    ToolCatalog,
    get_tool_catalog,
    get_tool_definition,
    get_tool_definition_by_display_name,
    resolve_tool_definition,
    create_fallback_tool_definition,
    get_all_tool_definitions,
    is_known_tool,
)

__all__ = [
    "ToolCategory",
    "CATEGORY_TO_VISUAL",
    "ToolCapabilities",
    "ToolDefinition",
    "ToolCatalog",
    "get_tool_catalog",
    "get_tool_definition",
    "get_tool_definition_by_display_name",
    "resolve_tool_definition",
    "create_fallback_tool_definition",
    "get_all_tool_definitions",
    "is_known_tool",
]
