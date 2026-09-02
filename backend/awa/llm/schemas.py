"""Schemas for LLM facts extraction, prompt payloads, and narrative outputs."""

from __future__ import annotations

from dataclasses import dataclass, field, field as dc_field
from typing import Any, Literal


@dataclass
class NarrativeResult:
    """A generated narrative text with provenance metadata."""
    text: str
    source: Literal["llm", "deterministic_fallback"]
    model: str = ""
    prompt_version: str = "2.0"
    is_cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "is_cached": self.is_cached,
        }


@dataclass
class BusinessPurposeResult:
    """A generated workflow business purpose narrative, business function, and normalized business-area tag."""
    business_purpose: str
    business_area_tag: str
    source: Literal["llm", "deterministic_fallback"]
    business_function: str = ""
    business_area_taxonomy_version: str = "3.0"
    classification_conflict: bool = False
    classification_evidence: list[str] = field(default_factory=list)
    model: str = ""
    prompt_version: str = "3.1"
    is_cached: bool = False

    @property
    def text(self) -> str:
        """Backward-compatible property for callers expecting NarrativeResult.text."""
        return self.business_purpose

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_purpose": self.business_purpose,
            "business_function": self.business_function,
            "business_area_tag": self.business_area_tag,
            "source": self.source,
            "business_area_taxonomy_version": self.business_area_taxonomy_version,
            "classification_conflict": self.classification_conflict,
            "classification_evidence": self.classification_evidence,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "is_cached": self.is_cached,
        }

@dataclass
class FactorAssessment:
    """Assessment of an individual criticality dimension."""
    dimension: str
    assessment: Literal["HIGH", "MEDIUM", "LOW", "NOT_ESTABLISHED"]
    evidence: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "assessment": self.assessment,
            "evidence": self.evidence,
            "rationale": self.rationale,
        }


@dataclass
class CriticalityEvidencePackage:
    """Compact deterministic evidence package supplied to LLM for criticality evaluation."""
    workflow_id: str
    workflow_filename: str
    business_purpose: str
    business_function: str
    business_area: str
    production_targets: list[str] = field(default_factory=list)
    inspection_sinks: list[str] = field(default_factory=list)
    upstream_producers: list[str] = field(default_factory=list)
    downstream_consumers: list[str] = field(default_factory=list)
    shared_targets: list[str] = field(default_factory=list)
    shared_sources: list[str] = field(default_factory=list)
    dependency_position: str = "Isolated"
    deterministic_counts: dict[str, int] = field(default_factory=dict)
    semantic_impact_signals: list[str] = field(default_factory=list)
    operational_metadata: dict[str, Any] = field(default_factory=dict)
    deterministic_reference_score: float | None = None
    deterministic_reference_level: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_filename": self.workflow_filename,
            "business_purpose": self.business_purpose,
            "business_function": self.business_function,
            "business_area": self.business_area,
            "production_targets": self.production_targets,
            "inspection_sinks": self.inspection_sinks,
            "upstream_producers": self.upstream_producers,
            "downstream_consumers": self.downstream_consumers,
            "shared_targets": self.shared_targets,
            "shared_sources": self.shared_sources,
            "dependency_position": self.dependency_position,
            "deterministic_counts": self.deterministic_counts,
            "semantic_impact_signals": self.semantic_impact_signals,
            "operational_metadata": self.operational_metadata,
            "deterministic_reference_score": self.deterministic_reference_score,
            "deterministic_reference_level": self.deterministic_reference_level,
        }


@dataclass
class CriticalityAssessmentResult:
    """Full LLM-driven criticality assessment result with auditable evidence."""
    criticality_score: float
    criticality_level: Literal["HIGH", "MEDIUM", "LOW"]
    factor_assessments: dict[str, FactorAssessment] = field(default_factory=dict)
    criticality_justification: str = ""
    business_consequence: str = ""
    dependency_impact: str = ""
    affected_scope: str = ""
    migration_implication: str = ""
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    source: Literal["llm", "deterministic_fallback"] = "deterministic_fallback"
    assessment_version: str = "2.0"
    model: str = ""
    prompt_version: str = "2.0"
    is_cached: bool = False
    criticality_factors: list[str] = field(default_factory=list)
    deterministic_reference_score: float | None = None

    @property
    def text(self) -> str:
        """Backward-compatible property for callers expecting NarrativeResult.text."""
        return self.criticality_justification

    def to_dict(self) -> dict[str, Any]:
        return {
            "criticality_score": self.criticality_score,
            "criticality_level": self.criticality_level,
            "factor_assessments": {
                k: v.to_dict() if hasattr(v, "to_dict") else v
                for k, v in self.factor_assessments.items()
            },
            "criticality_justification": self.criticality_justification,
            "business_consequence": self.business_consequence,
            "dependency_impact": self.dependency_impact,
            "affected_scope": self.affected_scope,
            "migration_implication": self.migration_implication,
            "confidence": self.confidence,
            "source": self.source,
            "assessment_version": self.assessment_version,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "is_cached": self.is_cached,
            "criticality_factors": self.criticality_factors,
            "deterministic_reference_score": self.deterministic_reference_score,
        }


@dataclass
class ToolFacts:
    """Deterministic factual context for a single tool instance in an ETL workflow."""
    tool_id: int
    tool_type: str
    plugin: str
    tool_name: str
    workflow_name: str
    workflow_role: str
    annotation: str
    deterministic_tool_definition: str
    configuration_summary: dict[str, Any] = dc_field(default_factory=dict)
    input_fields: list[str] = dc_field(default_factory=list)
    output_fields: list[str] = dc_field(default_factory=list)
    upstream_tools: list[dict[str, Any]] = dc_field(default_factory=list)
    downstream_tools: list[dict[str, Any]] = dc_field(default_factory=list)
    container_name: str | None = None
    container_context: str | None = None
    raw_node_xml: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "tool_id": self.tool_id,
            "tool_type": self.tool_type,
            "plugin": self.plugin,
            "tool_name": self.tool_name,
            "deterministic_tool_definition": self.deterministic_tool_definition,
            "workflow_role": self.workflow_role,
            "annotation": self.annotation,
            "configuration": self.configuration_summary,
            "input_fields": self.input_fields,
            "output_fields": self.output_fields,
            "upstream_tools": self.upstream_tools,
            "downstream_tools": self.downstream_tools,
            "container_context": self.container_context or self.container_name or "None",
        }


@dataclass
class WorkflowFacts:
    """Deterministic factual context for the entire workflow."""
    name: str
    version: str
    description: str
    total_tools: int
    source_inputs: list[dict[str, Any]] = dc_field(default_factory=list)
    processing_stages: list[dict[str, Any]] = dc_field(default_factory=list)
    major_transformations: list[str] = dc_field(default_factory=list)
    business_rules: list[str] = dc_field(default_factory=list)
    business_outputs: list[dict[str, Any]] = dc_field(default_factory=list)
    one_line_purpose: str = ""
    why_it_matters: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.name,
            "workflow_version": self.version,
            "description": self.description,
            "total_tools": self.total_tools,
            "source_inputs": self.source_inputs,
            "processing_stages": self.processing_stages,
            "major_transformations": self.major_transformations,
            "business_rules": self.business_rules,
            "business_outputs": self.business_outputs,
            "one_line_purpose": self.one_line_purpose,
            "why_it_matters": self.why_it_matters,
        }


@dataclass
class BusinessReportInputItem:
    source_dataset: str
    business_role: str
    source_format: str
    dependency_significance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_dataset": self.source_dataset,
            "business_role": self.business_role,
            "source_format": self.source_format,
            "dependency_significance": self.dependency_significance,
        }


@dataclass
class BusinessReportOutputItem:
    output_deliverable: str
    what_it_represents: str
    business_use: str
    destination_format: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_deliverable": self.output_deliverable,
            "what_it_represents": self.what_it_represents,
            "business_use": self.business_use,
            "destination_format": self.destination_format,
        }


@dataclass
class BusinessReportStageItem:
    stage_number: int
    stage_name: str
    description: str
    operational_explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "description": self.description,
            "operational_explanation": self.operational_explanation,
        }


@dataclass
class BusinessReportRuleItem:
    business_rule: str
    category: str
    evidence_configuration: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_rule": self.business_rule,
            "category": self.category,
            "evidence_configuration": self.evidence_configuration,
        }


@dataclass
class BusinessReportLineageItem:
    source_datasets: str | list[str]
    major_business_transformation: str
    target_deliverable: str

    def to_dict(self) -> dict[str, Any]:
        srcs = self.source_datasets if isinstance(self.source_datasets, str) else " + ".join(self.source_datasets)
        return {
            "source_datasets": srcs,
            "major_business_transformation": self.major_business_transformation,
            "target_deliverable": self.target_deliverable,
        }


@dataclass
class BusinessReportContent:
    """Structured LLM-authored content for the complete Business Report."""
    workflow_title: str
    workflow_description: str
    executive_summary: str
    methods_of_analysis: str
    findings: list[str]
    conclusions: str
    inputs: list[BusinessReportInputItem] = dc_field(default_factory=list)
    outputs: list[BusinessReportOutputItem] = dc_field(default_factory=list)
    sequential_stages: list[BusinessReportStageItem] = dc_field(default_factory=list)
    business_rules: list[BusinessReportRuleItem] = dc_field(default_factory=list)
    lineage: list[BusinessReportLineageItem] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_title": self.workflow_title,
            "workflow_description": self.workflow_description,
            "executive_summary": self.executive_summary,
            "methods_of_analysis": self.methods_of_analysis,
            "findings": self.findings,
            "conclusions": self.conclusions,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "sequential_stages": [s.to_dict() for s in self.sequential_stages],
            "business_rules": [r.to_dict() for r in self.business_rules],
            "lineage": [l.to_dict() for l in self.lineage],
        }


@dataclass
class ComprehensiveWorkflowContext:
    """Authoritative facts extracted deterministically from CIR and DAG to ground the LLM."""
    workflow_name: str
    workflow_version: str
    workflow_description: str
    author: str
    total_tools: int
    total_connections: int
    inputs: list[dict[str, Any]] = dc_field(default_factory=list)
    outputs: list[dict[str, Any]] = dc_field(default_factory=list)
    containers: list[dict[str, Any]] = dc_field(default_factory=list)
    execution_steps: list[dict[str, Any]] = dc_field(default_factory=list)
    rules_and_formulas: list[dict[str, Any]] = dc_field(default_factory=list)
    lineage_traces: list[dict[str, Any]] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_metadata": {
                "name": self.workflow_name,
                "version": self.workflow_version,
                "description": self.workflow_description,
                "author": self.author,
                "total_tools": self.total_tools,
                "total_connections": self.total_connections,
            },
            "inputs": self.inputs,
            "outputs": self.outputs,
            "containers": self.containers,
            "execution_steps": self.execution_steps,
            "rules_and_formulas": self.rules_and_formulas,
            "lineage_traces": self.lineage_traces,
        }


@dataclass
class ProcessStageContent:
    """Structured LLM-authored content for an individual process stage."""
    stage_number: int
    stage_name: str
    category: str
    description: str
    purpose: str
    transformation: str
    key_actions: list[str] = dc_field(default_factory=list)
    tool_ids: list[int] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "category": self.category,
            "description": self.description,
            "purpose": self.purpose,
            "transformation": self.transformation,
            "key_actions": self.key_actions,
            "tool_ids": self.tool_ids,
        }


@dataclass
class WorkflowProcessStages:
    """Collection of LLM-generated process stages for a workflow."""
    stages: list[ProcessStageContent] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": [s.to_dict() for s in self.stages],
        }


@dataclass
class STTMMappingItem:
    """Individual field-level mapping item resolved by LLM."""
    source_table: str
    source_attribute: str
    transformation: str
    transformation_logic: str
    target_table: str
    target_attribute: str
    source_tool_id: int | None = None
    target_tool_id: int | None = None
    evidence_tool_ids: list[int] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_table": self.source_table,
            "source_attribute": self.source_attribute,
            "transformation": self.transformation,
            "transformation_logic": self.transformation_logic,
            "target_table": self.target_table,
            "target_attribute": self.target_attribute,
            "source_tool_id": self.source_tool_id,
            "target_tool_id": self.target_tool_id,
            "evidence_tool_ids": self.evidence_tool_ids,
        }


@dataclass
class STTMLLMResponse:
    """Collection of LLM-resolved STTM mapping rows."""
    workflow_name: str
    mappings: list[STTMMappingItem] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "mappings": [m.to_dict() for m in self.mappings],
        }

