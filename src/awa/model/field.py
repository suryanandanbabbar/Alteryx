"""Field (column schema) model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    """Represents a column/field in a record schema.
    
    Attributes:
        name: Field name.
        type: Alteryx type string (e.g., 'V_WString', 'Double', 'Int32').
        size: Size constraint, if applicable.
        scale: Decimal scale, if applicable.
    """
    name: str
    type: str
    size: int | None = None
    scale: int | None = None

    def to_dict(self) -> dict:
        d: dict = {"name": self.name, "type": self.type}
        if self.size is not None:
            d["size"] = self.size
        if self.scale is not None:
            d["scale"] = self.scale
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Field:
        return cls(
            name=d["name"],
            type=d["type"],
            size=d.get("size"),
            scale=d.get("scale"),
        )
