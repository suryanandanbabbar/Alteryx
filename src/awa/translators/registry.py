"""Translator registry — 3-tier handler lookup.

Adapted from reference/alteryx2dbx/handlers/registry.py.
Uses exact plugin → tool type → prefix → UnsupportedTranslator fallback.
"""

from __future__ import annotations

from awa.model.tool import Tool
from .base import ToolTranslator, UnsupportedTranslator


class TranslatorRegistry:
    """Registry mapping Alteryx tool types to their translators.

    Lookup order:
    1. Exact plugin name match
    2. Tool type match
    3. Prefix match (for versioned plugins like box_input_v*)
    4. UnsupportedTranslator fallback
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
        """Look up the translator for a tool.

        Returns an instance of the matching translator,
        or UnsupportedTranslator if no match is found.
        """
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

        # 4. Fallback
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
