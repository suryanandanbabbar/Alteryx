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
    terminal_node_count: int = 0
    terminal_node_ids: list[int] = Field(default_factory=list)
    business_output_count: int = 0
    business_output_node_ids: list[int] = Field(default_factory=list)
    container_count: int = 0
    annotation_count: int = 0
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
    support_level: str = ""
    summary: str = ""
    annotation: str = ""
    output_fields: list[FieldDTO] = Field(default_factory=list)
    engine_settings: dict[str, str] = Field(default_factory=dict)
    visual_category: str
    container_id: int | None = None
    container_name: str | None = None
    raw_node_xml: str = ""
    xml_tool_name: str = ""


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
    summary: str = ""
    container_id: int | None = None
    container_name: str | None = None


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
    connections: list[ConnectionDTO] = Field(default_factory=list)
    diagnostics: list[DiagnosticDTO] = Field(default_factory=list)
    metrics: WorkflowMetricsDTO | None = None


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


# Business Intelligence DTOs
class BusinessInputDTO(BaseModel):
    tool_id: int
    name: str
    raw_source: str
    source_type: str
    sheet_or_table: str | None = None
    container_name: str | None = None
    business_role: str = ""
    description: str = ""


class BusinessOutputDTO(BaseModel):
    tool_id: int
    name: str
    raw_destination: str
    destination_type: str
    sheet_or_table: str | None = None
    business_meaning: str = ""
    likely_use: str = "Use not documented"
    business_purpose: str = ""
    container_name: str | None = None
    upstream_sources: list[str] = Field(default_factory=list)


class BusinessStageDTO(BaseModel):
    stage_number: int
    name: str
    short_title: str = ""
    summary: str = ""
    description: str = ""
    business_purpose: str = ""
    major_transformation: str = ""
    tool_ids: list[int] = Field(default_factory=list)
    input_ids: list[int] = Field(default_factory=list)
    output_ids: list[int] = Field(default_factory=list)
    tool_count: int = 0
    container_name: str | None = None
    annotations: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)


class BusinessTransformationDTO(BaseModel):
    category: str
    description: str
    affected_fields: list[str] = Field(default_factory=list)
    tool_ids: list[int] = Field(default_factory=list)


class BusinessRuleDTO(BaseModel):
    rule_name: str
    category: str
    description: str
    tool_ids: list[int] = Field(default_factory=list)
    evidence: str = ""


class BusinessLineageDTO(BaseModel):
    source_name: str
    transformation: str = ""
    target_name: str
    intermediate_stages: list[str] = Field(default_factory=list)
    transformation_summary: str = ""
    source_tool_id: int = 0
    target_tool_id: int = 0


class BusinessAssessmentDTO(BaseModel):
    complexity: str = "Moderate"
    complexity_reason: str = ""
    complexity_factors: list[str] = Field(default_factory=list)
    platform: str = "Alteryx Designer"
    business_owner: str = "Not documented"
    schedule: str = "Not documented"
    criticality: str = "Not documented"
    documentation_quality: str = "Partially documented"
    assessment_status: str = "Automated assessment"
    key_observations: list[str] = Field(default_factory=list)
    key_activities: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    role_and_value: list[str] = Field(default_factory=list)
    assessment_gaps: list[dict[str, str]] = Field(default_factory=list)
    preliminary_disposition: str = "Further assessment required"
    disposition_rationale: str = ""
    validation_checklist: list[str] = Field(default_factory=list)
    why_it_matters: str = ""


class WorkflowBusinessSummaryDTO(BaseModel):
    business_purpose: str
    one_line_purpose: str = ""
    why_it_matters: str = ""
    source_inputs: list[BusinessInputDTO] = Field(default_factory=list)
    processing_stages: list[BusinessStageDTO] = Field(default_factory=list)
    transformations: list[BusinessTransformationDTO] = Field(default_factory=list)
    business_rules: list[BusinessRuleDTO] = Field(default_factory=list)
    lineage: list[BusinessLineageDTO] = Field(default_factory=list)
    business_outputs: list[BusinessOutputDTO] = Field(default_factory=list)
    assessment: BusinessAssessmentDTO = Field(default_factory=BusinessAssessmentDTO)
    process_overview: str = ""
    information_flow: list[str] = Field(default_factory=list)
    overall_interpretation: str = ""
    confidence_level: str = "High"


class AnalysisOverviewDTO(BaseModel):
    analysis_id: str
    source: SourceInfoDTO
    metadata: WorkflowMetadataDTO
    metrics: WorkflowMetricsDTO
    execution_order: list[ExecutionStepDTO]
    connections: list[ConnectionDTO]
    diagnostics: list[DiagnosticDTO]
    business_summary: WorkflowBusinessSummaryDTO | None = None
