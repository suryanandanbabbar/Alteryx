"""Strongly-typed ToolDefinition model for Alteryx tool registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from awa.model.diagnostic import SupportLevel
from awa.tools.categories import ToolCategory, CATEGORY_TO_VISUAL
from awa.tools.capabilities import ToolCapabilities


@dataclass(frozen=True)
class ToolDefinition:
    """Canonical definition of an Alteryx Designer tool.
    
    Attributes:
        xml_name: Primary canonical XML plugin identifier (e.g. 'AlteryxBasePluginsGui.Filter.Filter').
        display_name: Human-readable official display name (e.g. 'Filter').
        category: Authoritative category (e.g. 'Preparation').
        support_level: Capability classification (FULL, PARTIAL, PASS_THROUGH, DOCUMENTATION_ONLY, EXTERNAL_EXECUTION, UNSUPPORTED).
        alters_data: Whether this tool alters record data or schemas.
        is_blocking: Whether this tool must buffer all records before emitting output (e.g. Sort, Summarize).
        is_macro: Whether the tool is implemented as an Alteryx macro (.yxmc).
        has_python_translation: Whether a deterministic Python translator exists.
        translator_name: Name of registered translator class (or None).
        parser_name: Name of specialized parser function (or None).
        input_anchors: Tuple of supported input anchor names (e.g. ('Input',), ('Left', 'Right')).
        output_anchors: Tuple of supported output anchor names (e.g. ('True', 'False'), ('Output',)).
        aliases: Alternative XML names or plugin aliases observed in workflows.
        description: Description of tool purpose and behavior.
        visual_category: Visual category override for graph and UI color rendering.
    """
    xml_name: str
    display_name: str
    category: ToolCategory | str

    support_level: SupportLevel

    alters_data: bool
    is_blocking: bool
    is_macro: bool

    has_python_translation: bool

    translator_name: str | None = None
    parser_name: str | None = None

    input_anchors: tuple[str, ...] = ()
    output_anchors: tuple[str, ...] = ()

    aliases: tuple[str, ...] = ()
    description: str = ""
    visual_category: str = ""

    def get_visual_category(self) -> str:
        """Return the visual category string for styling and graph rendering."""
        if self.visual_category:
            return self.visual_category
        cat_enum = self.category if isinstance(self.category, ToolCategory) else None
        if cat_enum and cat_enum in CATEGORY_TO_VISUAL:
            return CATEGORY_TO_VISUAL[cat_enum]
        return "transform"

    @property
    def capabilities(self) -> ToolCapabilities:
        """Return tool capabilities based on support level."""
        return ToolCapabilities(
            parsed=True,
            configuration=True,
            graph=True,
            python=self.has_python_translation,
            documentation=True,
            support_level=self.support_level,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize tool definition to dictionary."""
        cat_str = self.category.value if isinstance(self.category, ToolCategory) else str(self.category)
        return {
            "xml_name": self.xml_name,
            "display_name": self.display_name,
            "category": cat_str,
            "support_level": self.support_level.value,
            "alters_data": self.alters_data,
            "is_blocking": self.is_blocking,
            "is_macro": self.is_macro,
            "has_python_translation": self.has_python_translation,
            "translator_name": self.translator_name,
            "input_anchors": list(self.input_anchors),
            "output_anchors": list(self.output_anchors),
            "aliases": list(self.aliases),
            "description": self.description,
            "visual_category": self.get_visual_category(),
            "capabilities": self.capabilities.to_dict(),
        }
