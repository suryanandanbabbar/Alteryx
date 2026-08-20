"""ToolContainer model for visual grouping in Alteryx workflows."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any
from .tool import Position


@dataclass
class ToolContainer:
    """A ToolContainer grouping node in the workflow."""
    tool_id: int
    caption: str
    disabled: bool = False
    folded: bool = False
    parent_container_id: int | None = None
    child_tool_ids: list[int] = dc_field(default_factory=list)
    position: Position | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "tool_id": self.tool_id,
            "caption": self.caption,
            "disabled": self.disabled,
            "folded": self.folded,
            "child_tool_ids": self.child_tool_ids,
        }
        if self.parent_container_id is not None:
            d["parent_container_id"] = self.parent_container_id
        if self.position is not None:
            d["position"] = self.position.to_dict()
        return d
