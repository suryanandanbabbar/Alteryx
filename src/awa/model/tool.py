"""Tool model — a node in the workflow graph."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

from .field import Field


@dataclass(frozen=True)
class Position:
    """Canvas position of a tool."""
    x: int
    y: int

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass
class ToolConfiguration:
    """Tool-specific configuration.
    
    Attributes:
        raw_xml: The raw XML string of the <Configuration> element. Always preserved.
        parsed: Tool-specific parsed configuration as a dictionary.
    """
    raw_xml: str
    parsed: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "raw_xml": self.raw_xml,
            "parsed": self.parsed,
        }


@dataclass
class Tool:
    """An Alteryx tool (node) in the workflow.
    
    Attributes:
        tool_id: Unique numeric tool identifier.
        plugin: Full plugin string (e.g., 'AlteryxBasePluginsGui.Filter.Filter').
        tool_type: Derived type name (e.g., 'Filter').
        name: Annotation/display name.
        position: Canvas position, if available.
        configuration: Tool-specific configuration.
        annotation: Full annotation text.
        output_fields: Output field schema from MetaInfo/RecordInfo.
        engine_settings: Engine execution settings (EngineDll, EngineDllEntryPoint, etc.).
    """
    tool_id: int
    plugin: str
    tool_type: str
    name: str
    position: Position | None
    configuration: ToolConfiguration
    annotation: str = ""
    output_fields: list[Field] = dc_field(default_factory=list)
    engine_settings: dict[str, str] = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "tool_id": self.tool_id,
            "plugin": self.plugin,
            "tool_type": self.tool_type,
            "name": self.name,
            "configuration": self.configuration.to_dict(),
            "annotation": self.annotation,
            "output_fields": [f.to_dict() for f in self.output_fields],
        }
        if self.position is not None:
            d["position"] = self.position.to_dict()
        if self.engine_settings:
            d["engine_settings"] = self.engine_settings
        return d
