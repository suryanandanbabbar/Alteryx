"""Annotation and TextBox model for Alteryx workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from .tool import Position


@dataclass
class TextBoxNode:
    """A TextBox documentation annotation on the canvas."""
    tool_id: int
    text: str
    position: Position | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tool_id": self.tool_id,
            "text": self.text,
        }
        if self.position is not None:
            d["position"] = self.position.to_dict()
        return d
