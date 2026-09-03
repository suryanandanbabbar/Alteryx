"""Pydantic schemas and DTOs for the AWA REST API."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator


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
    source_filename: str | None = None
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
    likely_use: str = ""
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
    business_function: str = ""
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
    business_area_tag: str = "UNCLASSIFIED"
    business_area_tag_source: str = "deterministic_fallback"
    business_area_taxonomy_version: str = "3.0"
    criticality_score: float = 0.0
    criticality_level: str = "LOW"
    criticality_justification: str = ""
    criticality_business_consequence: str = ""
    criticality_dependency_impact: str = ""
    criticality_affected_scope: str = ""
    criticality_migration_implication: str = ""
    criticality_confidence: str = "HIGH"
    criticality_source: str = "deterministic_fallback"
    criticality_factors: list[str] = Field(default_factory=list)
    factor_assessments: dict[str, Any] = Field(default_factory=dict)


class FactorAssessmentDTO(BaseModel):
    dimension: str
    assessment: str
    evidence: str
    rationale: str



class AnalysisOverviewDTO(BaseModel):
    analysis_id: str
    source: SourceInfoDTO
    metadata: WorkflowMetadataDTO
    metrics: WorkflowMetricsDTO
    execution_order: list[ExecutionStepDTO]
    connections: list[ConnectionDTO]
    diagnostics: list[DiagnosticDTO]
    business_summary: WorkflowBusinessSummaryDTO | None = None


# ---------------------------------------------------------------------------
# Portfolio & ETL Rationalisation DTOs
# ---------------------------------------------------------------------------


class BusinessAreaClassificationDTO(BaseModel):
    business_area: str = "UNCLASSIFIED"
    confidence: str = "UNCLASSIFIED"
    evidence: list[str] = Field(default_factory=list)
    classification_source: str = "deterministic_fallback"
    secondary_business_areas: list[str] = Field(default_factory=list)
    classification_conflict: bool = False
    business_area_taxonomy_version: str = "3.0"


class PortfolioWorkflowSummaryDTO(BaseModel):
    workflow_id: str
    analysis_id: str = ""
    filename: str
    relative_path: str
    status: str
    error_message: str | None = None
    node_count: int = 0
    connection_count: int = 0
    source_count: int = 0
    target_count: int = 0
    sources: list[str] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    inspection_sinks: list[str] = Field(default_factory=list)
    sink_classifications: dict[str, str] = Field(default_factory=dict)
    tool_types: list[str] = Field(default_factory=list)
    business_purpose: str = ""
    business_function: str = ""
    sttm_mappings_count: int = 0
    business_area: BusinessAreaClassificationDTO = Field(default_factory=BusinessAreaClassificationDTO)
    business_area_tag: str = "UNCLASSIFIED"
    business_area_tag_source: str = "deterministic_fallback"
    business_area_taxonomy_version: str = "3.0"
    complexity_score: float = 0.0
    complexity_level: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    complexity_factors: list[str] = Field(default_factory=list)
    criticality_score: float = 0.0
    criticality_level: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    criticality_factors: list[str] = Field(default_factory=list)
    criticality_justification: str = ""
    criticality_business_consequence: str = ""
    criticality_dependency_impact: str = ""
    criticality_affected_scope: str = ""
    criticality_migration_implication: str = ""
    business_consequence: str = ""
    dependency_impact: str = ""
    affected_scope: str = ""
    migration_implication: str = ""
    criticality_confidence: str = "HIGH"
    criticality_source: str = "deterministic_fallback"
    factor_assessments: dict[str, Any] = Field(default_factory=dict)
    last_run: str = "Not documented"
    frequency: str = "Not documented"


class DeterministicSignalsDTO(BaseModel):
    shared_sources: list[str] = Field(default_factory=list)
    shared_targets: list[str] = Field(default_factory=list)
    tool_sequence_similarity: float = 0.0
    graph_topology_similarity: float = 0.0
    transformation_overlap: float = 0.0
    field_overlap: float = 0.0
    lineage_overlap: float = 0.0
    composite_score: float = 0.0


class WorkflowRelationshipDTO(BaseModel):
    workflow_a_id: str
    workflow_a_name: str
    workflow_b_id: str
    workflow_b_name: str
    relationship_type: str
    deterministic_signals: DeterministicSignalsDTO
    llm_reasoning: str = ""
    confidence: str = "HIGH"
    evidence: list[str] = Field(default_factory=list)


class DeterministicMetricsDTO(BaseModel):
    source_overlap: float = 0.0
    target_overlap: float = 0.0
    transformation_similarity: float = 0.0
    schema_similarity: float = 0.0
    grain_similarity: float = 0.0
    dag_similarity: float = 0.0
    frequency_overlap: float = 0.0


class RiskContextDTO(BaseModel):
    complexity_by_workflow: dict[str, str] = Field(default_factory=dict)
    criticality_by_workflow: dict[str, str] = Field(default_factory=dict)
    risk_level: str = "LOW"
    risk_notes: list[str] = Field(default_factory=list)


class OutputEvidenceDTO(BaseModel):
    production_targets: dict[str, list[str]] = Field(default_factory=dict)
    inspection_sinks: dict[str, list[str]] = Field(default_factory=dict)
    output_schemas: dict[str, list[str]] = Field(default_factory=dict)
    output_grains: dict[str, list[str]] = Field(default_factory=dict)
    is_equivalent_target: bool = False
    is_equivalent_schema: bool = False
    is_equivalent_grain: bool = False


class DependencyEvidenceDTO(BaseModel):
    downstream_consumers: dict[str, list[str]] = Field(default_factory=dict)
    upstream_producers: dict[str, list[str]] = Field(default_factory=dict)
    shared_sources: list[str] = Field(default_factory=list)
    shared_targets: list[str] = Field(default_factory=list)
    dependency_status: str = "NOT_FOUND_IN_PORTFOLIO"
    dependency_notes: str = ""


class ConsolidationDecisionDTO(BaseModel):
    recommendation: Literal["MERGE", "DO NOT MERGE"] = "DO NOT MERGE"
    matched_rule: str = ""
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)
    source_overlap_pct: float = 0.0
    is_source_100_pct: bool = False
    output_relationship: str = ""
    complexity_a: str = "LOW"
    complexity_b: str = "LOW"
    frequency_a: str = "Not documented"
    frequency_b: str = "Not documented"
    is_same_frequency: bool = False
    logic_preservable: bool = False
    merge_direction: Optional[str] = None


class RationalisationCandidateDTO(BaseModel):
    candidate_id: str = ""
    workflow_ids: list[str]
    workflow_names: list[str]
    recommendation_type: Literal["CONSOLIDATE", "RETIRE_CANDIDATE", "SHARED_LOGIC", "REVIEW", "NO_ACTION"]
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    opportunity_score: float = 0.0
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)
    shared_logic: list[str] = Field(default_factory=list)
    unique_functionality: dict[str, list[str]] = Field(default_factory=dict)
    proposed_strategy: str = ""
    validation_requirements: list[str] = Field(default_factory=list)
    deterministic_metrics: DeterministicMetricsDTO = Field(default_factory=DeterministicMetricsDTO)
    output_evidence: OutputEvidenceDTO = Field(default_factory=OutputEvidenceDTO)
    dependency_evidence: DependencyEvidenceDTO = Field(default_factory=DependencyEvidenceDTO)
    risk_context: RiskContextDTO = Field(default_factory=RiskContextDTO)
    admissible_recommendations: list[str] = Field(default_factory=list)
    llm_enrichment_status: str = "DETERMINISTIC_BASELINE"
    consolidation_decision: Optional[ConsolidationDecisionDTO] = None
    sources_by_workflow: dict[str, list[str]] = Field(default_factory=dict)
    source_fields_by_workflow: dict[str, dict[str, list[str]]] = Field(default_factory=dict)
    transformations_by_workflow: dict[str, list[str]] = Field(default_factory=dict)
    frequencies_by_workflow: dict[str, str] = Field(default_factory=dict)

    @field_validator("shared_logic", mode="before")
    @classmethod
    def sanitize_shared_logic(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        from awa.analysis.rationalisation_analyzer import is_meaningful_evidence
        return [str(item).strip() for item in v if is_meaningful_evidence(str(item))]

    @field_validator("unique_functionality", mode="before")
    @classmethod
    def sanitize_unique_functionality(cls, v: Any) -> dict[str, list[str]]:
        if not isinstance(v, dict):
            return {}
        from awa.analysis.rationalisation_analyzer import is_meaningful_evidence
        cleaned: dict[str, list[str]] = {}
        for k, items in v.items():
            if isinstance(items, list):
                valid_items = [str(it).strip() for it in items if is_meaningful_evidence(str(it))]
                if valid_items:
                    cleaned[k] = valid_items
        return cleaned


class RationalisationAnalysisDTO(BaseModel):
    portfolio_id: str
    candidates: list[RationalisationCandidateDTO] = Field(default_factory=list)
    total_opportunities: int = 0
    recommendation_counts: dict[str, int] = Field(default_factory=dict)
    analysed_workflow_count: int = 0


class SharedDatasetDTO(BaseModel):
    dataset_name: str
    dataset_type: str
    workflow_ids: list[str]
    workflow_names: list[str]


class PortfolioAggregateMetricsDTO(BaseModel):
    total_workflows: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    total_tools: int = 0
    total_sources: int = 0
    unique_sources: int = 0
    total_targets: int = 0
    unique_targets: int = 0
    shared_sources_count: int = 0
    shared_targets_count: int = 0
    inspection_sinks_count: int = 0
    tool_distribution: dict[str, int] = Field(default_factory=dict)


class BusinessAreaGroupDTO(BaseModel):
    business_area: str
    workflow_count: int = 0
    workflows: list[PortfolioWorkflowSummaryDTO] = Field(default_factory=list)
    description: str = ""


class PortfolioOverviewDTO(BaseModel):
    portfolio_id: str
    portfolio_name: str
    workflow_count: int
    workflows: list[PortfolioWorkflowSummaryDTO]
    metrics: PortfolioAggregateMetricsDTO
    shared_sources: list[SharedDatasetDTO]
    shared_targets: list[SharedDatasetDTO]
    relationships: list[WorkflowRelationshipDTO]
    rationalisation_candidates: list[RationalisationCandidateDTO]
    business_area_counts: dict[str, int] = Field(default_factory=dict)
    business_area_descriptions: dict[str, str] = Field(default_factory=dict)
    business_areas: list[BusinessAreaGroupDTO] = Field(default_factory=list)
    created_at: float

