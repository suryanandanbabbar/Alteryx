"""Central Tool Catalog and lookup service for Alteryx tools."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from awa.model.diagnostic import SupportLevel
from awa.tools.categories import ToolCategory
from awa.tools.definition import ToolDefinition
from awa.tools.definitions import ALL_TOOLS

DEFAULT_CUSTOM_TOOL_SUMMARY = "Custom or unregistered Alteryx tool preserved for workflow analysis."


class ToolCatalog:
    """Central registry catalog containing curated Alteryx tool definitions."""

    def __init__(self, tools: Iterable[ToolDefinition] = ALL_TOOLS) -> None:
        self._primary_tools: list[ToolDefinition] = list(tools)
        self._by_xml: dict[str, ToolDefinition] = {}
        self._by_display_name: dict[str, ToolDefinition] = {}
        self._by_normalized_name: dict[str, ToolDefinition] = {}
        self._by_alias: dict[str, ToolDefinition] = {}
        self._matrix_summaries: dict[str, str] = {}

        self._index_tools()
        self._load_matrix_summaries()

    def _index_tools(self) -> None:
        for tool in self._primary_tools:
            # Primary XML identifier index
            self._by_xml[tool.xml_name] = tool

            # Display name index
            self._by_display_name[tool.display_name] = tool
            self._by_normalized_name[self._normalize_name(tool.display_name)] = tool

            # Short XML name (e.g., 'DbFileInput' from 'AlteryxBasePluginsGui.DbFileInput.DbFileInput')
            short_name = tool.xml_name.rsplit(".", 1)[-1]
            if short_name not in self._by_alias:
                self._by_alias[short_name] = tool

            # Explicit aliases
            for alias in tool.aliases:
                self._by_alias[alias] = tool
                self._by_normalized_name[self._normalize_name(alias)] = tool

    def _load_matrix_summaries(self) -> None:
        """Load business summaries from docs/tool-support-matrix.md if present."""
        # Check potential candidate locations for the markdown matrix
        candidates = [
            Path(__file__).resolve().parents[3] / "docs" / "tool-support-matrix.md",
            Path.cwd() / "docs" / "tool-support-matrix.md",
        ]
        matrix_file: Path | None = None
        for candidate in candidates:
            if candidate.is_file():
                matrix_file = candidate
                break

        if not matrix_file:
            return

        try:
            with open(matrix_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith("|") or "XML Tool Name" in line or "---" in line:
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    # Format: | # | Category | Tool Name | XML Tool Name | Business Summary | ...
                    if len(parts) >= 6:
                        tool_name = parts[3]
                        xml_name = parts[4].strip("` ")
                        summary = parts[5].strip()
                        if xml_name and summary:
                            self._matrix_summaries[xml_name] = summary
                            self._matrix_summaries[self._normalize_name(xml_name)] = summary
                        if tool_name and summary:
                            self._matrix_summaries[tool_name] = summary
                            self._matrix_summaries[self._normalize_name(tool_name)] = summary
        except Exception:
            # Fall back gracefully to ToolDefinition.description
            pass

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize tool name for flexible matching (lowercase, no spaces/special chars)."""
        return "".join(c.lower() for c in name if c.isalnum())

    @property
    def primary_tool_count(self) -> int:
        """Return the count of primary curated tools in the catalog."""
        return len(self._primary_tools)

    def __len__(self) -> int:
        return len(self._primary_tools)

    def __iter__(self):
        return iter(self._primary_tools)

    def get(self, xml_name: str) -> ToolDefinition | None:
        """Look up tool definition by canonical XML identifier or alias."""
        if not xml_name:
            return None

        # 1. Exact canonical XML identifier
        if xml_name in self._by_xml:
            return self._by_xml[xml_name]

        # 2. Exact alias match
        if xml_name in self._by_alias:
            return self._by_alias[xml_name]

        # 3. Last dotted component match (e.g. Filter from AlteryxBasePluginsGui.Filter.Filter)
        short_name = xml_name.rsplit(".", 1)[-1]
        if short_name in self._by_alias:
            return self._by_alias[short_name]
        if short_name in self._by_xml:
            return self._by_xml[short_name]

        # 4. Normalized match
        norm = self._normalize_name(xml_name)
        if norm in self._by_normalized_name:
            return self._by_normalized_name[norm]

        return None

    def get_by_display_name(self, display_name: str) -> ToolDefinition | None:
        """Look up tool definition by exact or normalized display name."""
        if not display_name:
            return None

        if display_name in self._by_display_name:
            return self._by_display_name[display_name]

        norm = self._normalize_name(display_name)
        return self._by_normalized_name.get(norm)

    def get_summary(self, identifier: str) -> str:
        """Return the canonical business summary for a tool identifier."""
        if not identifier:
            return DEFAULT_CUSTOM_TOOL_SUMMARY

        # 1. Direct match in matrix summaries
        if identifier in self._matrix_summaries:
            return self._matrix_summaries[identifier]

        # 2. Normalized match in matrix summaries
        norm = self._normalize_name(identifier)
        if norm in self._matrix_summaries:
            return self._matrix_summaries[norm]

        # 3. Tool definition lookup
        defn = self.get(identifier) or self.get_by_display_name(identifier)
        if defn and defn.description:
            return defn.description

        return DEFAULT_CUSTOM_TOOL_SUMMARY

    def is_known(self, xml_name: str) -> bool:
        """Check if an XML tool name is recognized in the catalog."""
        return self.get(xml_name) is not None

    def get_all(self) -> list[ToolDefinition]:
        """Return all primary tool definitions in the catalog."""
        return list(self._primary_tools)

    def get_by_category(self, category: ToolCategory | str) -> list[ToolDefinition]:
        """Filter tools by category."""
        cat_val = category.value if isinstance(category, ToolCategory) else category
        return [t for t in self._primary_tools if (t.category.value if isinstance(t.category, ToolCategory) else str(t.category)) == cat_val]

    def get_by_support_level(self, support_level: SupportLevel) -> list[ToolDefinition]:
        """Filter tools by capability classification."""
        return [t for t in self._primary_tools if t.support_level == support_level]

    def create_fallback(self, xml_name: str) -> ToolDefinition:
        """Create a safe fallback ToolDefinition for an unknown or custom tool."""
        short_name = xml_name.rsplit(".", 1)[-1] if xml_name else "UnknownTool"
        return ToolDefinition(
            xml_name=xml_name or "UnknownPlugin.UnknownTool",
            display_name=short_name,
            category=ToolCategory.DEVELOPER,
            support_level=SupportLevel.UNSUPPORTED,
            alters_data=True,
            is_blocking=False,
            is_macro=xml_name.endswith(".yxmc") if xml_name else False,
            has_python_translation=False,
            translator_name="UnsupportedTranslator",
            parser_name=None,
            input_anchors=("Input",),
            output_anchors=("Output",),
            description=DEFAULT_CUSTOM_TOOL_SUMMARY,
            visual_category="transform",
        )

    def resolve(self, xml_name: str) -> ToolDefinition:
        """Resolve a tool definition, falling back to a safe unknown definition if not found."""
        definition = self.get(xml_name)
        if definition is not None:
            return definition
        return self.create_fallback(xml_name)


# Global catalog singleton instance
_catalog = ToolCatalog()


def get_tool_catalog() -> ToolCatalog:
    """Return the global tool catalog singleton."""
    return _catalog


def get_tool_definition(xml_name: str) -> ToolDefinition | None:
    """Look up a tool definition by XML plugin identifier or alias."""
    return _catalog.get(xml_name)


def get_tool_definition_by_display_name(display_name: str) -> ToolDefinition | None:
    """Look up a tool definition by display name."""
    return _catalog.get_by_display_name(display_name)


def get_tool_summary(identifier: str) -> str:
    """Look up the canonical business summary for a tool identifier or alias."""
    return _catalog.get_summary(identifier)


def resolve_tool_definition(xml_name: str) -> ToolDefinition:
    """Resolve a tool definition or return a safe fallback definition."""
    return _catalog.resolve(xml_name)


def create_fallback_tool_definition(xml_name: str) -> ToolDefinition:
    """Create a fallback tool definition for an unknown tool."""
    return _catalog.create_fallback(xml_name)


def get_all_tool_definitions() -> list[ToolDefinition]:
    """Return all primary tool definitions in the catalog."""
    return _catalog.get_all()


def is_known_tool(xml_name: str) -> bool:
    """Check whether a tool XML identifier is known."""
    return _catalog.is_known(xml_name)
