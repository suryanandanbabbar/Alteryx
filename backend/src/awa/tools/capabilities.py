"""Tool capabilities and support classification."""

from __future__ import annotations

from dataclasses import dataclass
from awa.model.diagnostic import SupportLevel


@dataclass(frozen=True)
class ToolCapabilities:
    """Detailed runtime capabilities of a tool."""
    parsed: bool = True
    configuration: bool = True
    graph: bool = True
    python: bool = False
    documentation: bool = True
    support_level: SupportLevel = SupportLevel.UNSUPPORTED

    def to_dict(self) -> dict[str, bool | str]:
        return {
            "level": self.support_level.value,
            "parsed": self.parsed,
            "configuration": self.configuration,
            "graph": self.graph,
            "python": self.python,
            "documentation": self.documentation,
        }
