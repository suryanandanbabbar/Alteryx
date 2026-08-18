"""Pydantic schemas and DTOs for the AWA REST API."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class PackageMetadataDTO(BaseModel):
    primary_workflow: str = ""
    contained_files: list[str] = Field(default_factory=list)
    total_size_bytes: int = 0


class SourceInfoDTO(BaseModel):
    source_format: str
    original_filename: str
    package_metadata: PackageMetadataDTO | None = None


class WorkflowMetadataDTO(BaseModel):
    name: str
    version: str
    author: str | None = None
    description: str | None = None


class WorkflowMetricsDTO(BaseModel):
    total_nodes: int
    total_connections: int
    input_count: int
    output_count: int
    input_node_ids: list[int] = Field(default_factory=list)
    output_node_ids: list[int] = Field(default_factory=list)
    support_summary: dict[str, int] = Field(default_factory=dict)


class PositionDTO(BaseModel):
    x: int
    y: int


class FieldDTO(BaseModel):
    name: str
    type: str
    size: int | None = None
    scale: int | None = None


class DiagnosticDTO(BaseModel):
    level: str
    category: str
    tool_id: int | None = None
    tool_type: str | None = None
    message: str
    detail: str | None = None


class DiagnosticsSummaryDTO(BaseModel):
    total_diagnostics: int
    by_level: dict[str, int] = Field(default_factory=dict)
    tool_support: dict[str, int] = Field(default_factory=dict)


class NodeDTO(BaseModel):
    tool_id: int
    tool_type: str
    name: str
    plugin: str
    position: PositionDTO | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    support_level: str
    annotation: str
    output_fields: list[FieldDTO] = Field(default_factory=list)
    engine_settings: dict[str, str] = Field(default_factory=dict)
    visual_category: str


class ConnectionDTO(BaseModel):
    origin_tool_id: int
    origin_anchor: str
    destination_tool_id: int
    destination_anchor: str


class ExecutionStepDTO(BaseModel):
    step_number: int
    tool_id: int
    tool_type: str
    name: str
    visual_category: str


class DagNodeLayoutDTO(BaseModel):
    tool_id: int
    x: float
    y: float
    width: float
    height: float
    label: str
    tool_type: str
    execution_index: int
    visual_category: str


class DagEdgeLayoutDTO(BaseModel):
    source_id: int
    target_id: int
    source_anchor: str
    target_anchor: str
    path_points: list[dict[str, float]] = Field(default_factory=list)


class DagLayoutDTO(BaseModel):
    nodes: list[DagNodeLayoutDTO] = Field(default_factory=list)
    edges: list[DagEdgeLayoutDTO] = Field(default_factory=list)
    width: float
    height: float
    title: str


class DiagramDTO(BaseModel):
    svg: str
    nodes: list[NodeDTO]
    dag_layout: DagLayoutDTO


class LibraryDTO(BaseModel):
    name: str
    import_statement: str
    reason: str


class PythonTraceDTO(BaseModel):
    tool_id: int
    tool_type: str
    tool_name: str
    start_line: int
    end_line: int
    description: str
    pandas_op: str
    reason: str
    libraries: list[str] = Field(default_factory=list)


class PythonOutputDTO(BaseModel):
    code: str
    required_libraries: list[str]
    trace_map: list[PythonTraceDTO]
    total_lines: int


class AnalysisOverviewDTO(BaseModel):
    analysis_id: str
    source: SourceInfoDTO
    metadata: WorkflowMetadataDTO
    metrics: WorkflowMetricsDTO
    execution_order: list[ExecutionStepDTO]
    connections: list[ConnectionDTO]
    diagnostics: list[DiagnosticDTO]
