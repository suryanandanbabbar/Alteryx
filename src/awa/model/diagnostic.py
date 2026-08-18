"""Diagnostic and dependency models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiagnosticLevel(Enum):
    """Severity level for diagnostics."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SupportLevel(Enum):
    """Classification of tool/feature support."""
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    EXTERNAL_DEPENDENCY = "external_dependency"


@dataclass
class Diagnostic:
    """A diagnostic message produced during analysis.
    
    Attributes:
        level: Severity level.
        category: Category string (e.g., 'unsupported_tool', 'parse_warning').
        tool_id: Associated tool ID, if applicable.
        tool_type: Associated tool type, if applicable.
        message: Human-readable message.
        detail: Additional detail, if any.
    """
    level: DiagnosticLevel
    category: str
    tool_id: int | None
    tool_type: str | None
    message: str
    detail: str | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
        }
        if self.tool_id is not None:
            d["tool_id"] = self.tool_id
        if self.tool_type is not None:
            d["tool_type"] = self.tool_type
        if self.detail is not None:
            d["detail"] = self.detail
        return d


@dataclass
class Dependency:
    """An external dependency referenced by the workflow.
    
    Attributes:
        dep_type: Type of dependency ('file', 'macro', 'database', 'credential').
        reference: The reference string (path, macro name, connection string).
        tool_id: Tool ID that references this dependency, if applicable.
        resolved: Whether the dependency can be resolved.
    """
    dep_type: str
    reference: str
    tool_id: int | None = None
    resolved: bool = False

    def to_dict(self) -> dict:
        d: dict = {
            "type": self.dep_type,
            "reference": self.reference,
            "resolved": self.resolved,
        }
        if self.tool_id is not None:
            d["tool_id"] = self.tool_id
        return d
