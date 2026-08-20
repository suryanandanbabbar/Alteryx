"""STTM (Source-to-Target Mapping) canonical data models."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


@dataclass
class STTMMapping:
    """Represents a single field-level source-to-target mapping row in the enterprise STTM workbook.

    Attributes:
        source_table: Business or dataset name of the originating source.
        source_attribute: Attribute/column name in the source dataset.
        transformation: Standard transformation category (e.g. Direct, Rename, Join, Derived Calculation, Aggregation, Filter, Union, Pivot / Reshape, Lookup, Conditional, Other Transformation).
        transformation_logic: Clear, business-readable description of how the target attribute is produced.
        target_table: Business or dataset name of the destination target.
        target_attribute: Attribute/column name in the target dataset.
        source_tool_id: Internal tool ID of the originating source node (for auditability).
        target_tool_id: Internal tool ID of the destination target node (for auditability).
        evidence: Optional internal evidence trace backing the mapping.
    """
    source_table: str
    source_attribute: str
    transformation: str
    transformation_logic: str
    target_table: str
    target_attribute: str
    source_tool_id: int | None = None
    target_tool_id: int | None = None
    evidence: str = ""

    def to_dict(self) -> dict:
        return {
            "source_table": self.source_table,
            "source_attribute": self.source_attribute,
            "transformation": self.transformation,
            "transformation_logic": self.transformation_logic,
            "target_table": self.target_table,
            "target_attribute": self.target_attribute,
        }


@dataclass
class STTMDocument:
    """Container holding the complete collection of STTM mappings for a workflow."""
    workflow_name: str
    mappings: list[STTMMapping] = dc_field(default_factory=list)

    @property
    def total_mappings(self) -> int:
        return len(self.mappings)

    def to_dict(self) -> dict:
        return {
            "workflow_name": self.workflow_name,
            "total_mappings": self.total_mappings,
            "mappings": [m.to_dict() for m in self.mappings],
        }
