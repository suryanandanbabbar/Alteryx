"""Connection model — directed edge in the workflow graph."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """A directed connection between two tools.
    
    Attributes:
        origin_tool_id: Source tool ID.
        origin_anchor: Source output anchor name (e.g., 'Output', 'True', 'Join').
        destination_tool_id: Target tool ID.
        destination_anchor: Target input anchor name (e.g., 'Input', 'Left', 'Right').
    """
    origin_tool_id: int
    origin_anchor: str
    destination_tool_id: int
    destination_anchor: str

    def to_dict(self) -> dict:
        return {
            "origin_tool_id": self.origin_tool_id,
            "origin_anchor": self.origin_anchor,
            "destination_tool_id": self.destination_tool_id,
            "destination_anchor": self.destination_anchor,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Connection:
        return cls(
            origin_tool_id=d["origin_tool_id"],
            origin_anchor=d["origin_anchor"],
            destination_tool_id=d["destination_tool_id"],
            destination_anchor=d["destination_anchor"],
        )
