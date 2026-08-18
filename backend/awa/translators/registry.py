"""Translator registry — unified registry-driven handler lookup."""

from __future__ import annotations

from awa.model.tool import Tool
from awa.model.diagnostic import SupportLevel
from awa.tools.catalog import get_tool_definition
from .base import (
    ToolTranslator,
    PassThroughTranslator,
    DocumentationTranslator,
    ExternalExecutionTranslator,
    PartialSupportTranslator,
    UnsupportedTranslator,
)


class TranslatorRegistry:
    """Registry mapping Alteryx tool types to their translators.

    Lookup order:
    1. Exact plugin name match
    2. Tool type match
    3. Prefix match (for versioned plugins)
    4. Canonical Tool Registry lookup (translator_name / capability mapping)
    5. UnsupportedTranslator fallback
    """

    def __init__(self) -> None:
        self._plugin_handlers: dict[str, type[ToolTranslator]] = {}
        self._type_handlers: dict[str, type[ToolTranslator]] = {}
        self._prefix_handlers: dict[str, type[ToolTranslator]] = {}

    def register_plugin(self, plugin: str, translator_cls: type[ToolTranslator]) -> None:
        """Register a translator for an exact plugin name."""
        self._plugin_handlers[plugin] = translator_cls

    def register_type(self, tool_type: str, translator_cls: type[ToolTranslator]) -> None:
        """Register a translator for a tool type."""
        self._type_handlers[tool_type] = translator_cls

    def register_prefix(self, prefix: str, translator_cls: type[ToolTranslator]) -> None:
        """Register a translator for a plugin name prefix."""
        self._prefix_handlers[prefix] = translator_cls

    def get(self, tool: Tool) -> ToolTranslator:
        """Look up the translator for a tool."""
        # 1. Exact plugin match
        cls = self._plugin_handlers.get(tool.plugin)
        if cls:
            return cls()

        # 2. Tool type match
        cls = self._type_handlers.get(tool.tool_type)
        if cls:
            return cls()

        # 3. Prefix match
        for prefix, cls in self._prefix_handlers.items():
            if tool.plugin.startswith(prefix) or tool.tool_type.startswith(prefix):
                return cls()

        # 4. Tool Registry catalog lookup
        tool_def = get_tool_definition(tool.plugin) or get_tool_definition(tool.tool_type)
        if tool_def:
            if tool_def.translator_name and tool_def.translator_name in self._type_handlers:
                return self._type_handlers[tool_def.translator_name]()
            if tool_def.support_level == SupportLevel.PASS_THROUGH:
                return PassThroughTranslator()
            if tool_def.support_level == SupportLevel.DOCUMENTATION_ONLY:
                return DocumentationTranslator()
            if tool_def.support_level == SupportLevel.EXTERNAL_EXECUTION:
                return ExternalExecutionTranslator()
            if tool_def.support_level == SupportLevel.PARTIAL:
                return PartialSupportTranslator()

        # 5. Fallback
        return UnsupportedTranslator()

    def supported_types(self) -> set[str]:
        """Return all registered tool types."""
        return set(self._type_handlers.keys())


# Global registry instance
_registry = TranslatorRegistry()


def get_translator(tool: Tool) -> ToolTranslator:
    """Look up the translator for a tool from the global registry."""
    return _registry.get(tool)


def register_type(tool_type: str, translator_cls: type[ToolTranslator]) -> None:
    """Register a translator for a tool type in the global registry."""
    _registry.register_type(tool_type, translator_cls)


def register_plugin(plugin: str, translator_cls: type[ToolTranslator]) -> None:
    """Register a translator for an exact plugin name in the global registry."""
    _registry.register_plugin(plugin, translator_cls)


def get_registry() -> TranslatorRegistry:
    """Return the global translator registry."""
    return _registry
