"""Canonical portfolio data models for Multi-Workflow Portfolio Analysis and ETL Rationalisation.

Follows the application's canonical model conventions:
- Strict separation of deterministic evidence from LLM interpretation
- Auditable multi-signal workflow similarity metrics
- Explicit classification of production outputs vs inspection sinks
- Complete JSON serializability via .to_dict()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BusinessAreaClassification:
    """Classification of a workflow into an enterprise business domain."""
    business_area: str = "UNCLASSIFIED"  # "Claims & Risk" | "Legal" | "Underwriting" | "Sales & Distribution" | "UNCLASSIFIED"
    confidence: str = "UNCLASSIFIED"  # "HIGH" | "MEDIUM" | "LOW" | "UNCLASSIFIED"
    evidence: list[str] = field(default_factory=list)  # Only actual output dataset names or column headers
    classification_source: str = "deterministic_fallback"  # "llm" | "deterministic_fallback"
    secondary_business_areas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_area": self.business_area,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "classification_source": self.classification_source,
            "secondary_business_areas": self.secondary_business_areas,
        }


@dataclass
class BusinessAreaGroup:
    """A business area with its assigned workflows and total count (which can be 0)."""
    business_area: str
    workflow_count: int = 0
    workflows: list[PortfolioWorkflowSummary] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_area": self.business_area,
            "workflow_count": self.workflow_count,
            "workflows": [w.to_dict() for w in self.workflows],
            "description": self.description,
        }


@dataclass
class PortfolioWorkflowSummary:
    """Canonical summary of an individual workflow within a portfolio."""
    workflow_id: str
    filename: str
    relative_path: str
    status: str  # "SUCCESS" | "FAILED"
    error_message: str | None = None
    node_count: int = 0
    connection_count: int = 0
    source_count: int = 0
    target_count: int = 0
    sources: list[str] = field(default_factory=list)  # Actual configured file names/paths
    targets: list[str] = field(default_factory=list)  # Actual production deliverables
    inspection_sinks: list[str] = field(default_factory=list)  # Terminal Browse/BrowseV2 sinks
    sink_classifications: dict[str, str] = field(default_factory=dict)  # sink_name -> PRODUCTION_OUTPUT | INSPECTION_SINK
    tool_types: list[str] = field(default_factory=list)
    business_purpose: str = ""
    sttm_mappings_count: int = 0
    business_area: BusinessAreaClassification = field(default_factory=BusinessAreaClassification)
    business_area_tag: str = "UNCLASSIFIED"
    business_area_tag_source: str = "deterministic_fallback"
    analysis_id: str = ""
    complexity_score: float = 0.0
    complexity_level: str = "LOW"  # "HIGH" | "MEDIUM" | "LOW"
    complexity_factors: list[str] = field(default_factory=list)
    criticality_score: float = 0.0
    criticality_level: str = "LOW"  # "HIGH" | "MEDIUM" | "LOW"
    criticality_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "analysis_id": self.analysis_id or self.workflow_id,
            "filename": self.filename,
            "relative_path": self.relative_path,
            "status": self.status,
            "error_message": self.error_message,
            "node_count": self.node_count,
            "connection_count": self.connection_count,
            "source_count": self.source_count,
            "target_count": self.target_count,
            "sources": self.sources,
            "targets": self.targets,
            "inspection_sinks": self.inspection_sinks,
            "sink_classifications": self.sink_classifications,
            "tool_types": self.tool_types,
            "business_purpose": self.business_purpose,
            "sttm_mappings_count": self.sttm_mappings_count,
            "business_area": self.business_area.to_dict() if self.business_area else BusinessAreaClassification().to_dict(),
            "business_area_tag": self.business_area_tag,
            "business_area_tag_source": self.business_area_tag_source,
            "complexity_score": self.complexity_score,
            "complexity_level": self.complexity_level,
            "complexity_factors": self.complexity_factors,
            "criticality_score": self.criticality_score,
            "criticality_level": self.criticality_level,
            "criticality_factors": self.criticality_factors,
        }


@dataclass
class DeterministicSignals:
    """Auditable multi-signal deterministic measurements between two workflows."""
    shared_sources: list[str] = field(default_factory=list)
    shared_targets: list[str] = field(default_factory=list)
    tool_sequence_similarity: float = 0.0
    graph_topology_similarity: float = 0.0
    transformation_overlap: float = 0.0
    field_overlap: float = 0.0
    lineage_overlap: float = 0.0
    composite_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "shared_sources": self.shared_sources,
            "shared_targets": self.shared_targets,
            "tool_sequence_similarity": round(self.tool_sequence_similarity, 3),
            "graph_topology_similarity": round(self.graph_topology_similarity, 3),
            "transformation_overlap": round(self.transformation_overlap, 3),
            "field_overlap": round(self.field_overlap, 3),
            "lineage_overlap": round(self.lineage_overlap, 3),
            "composite_score": round(self.composite_score, 3),
        }


@dataclass
class WorkflowRelationship:
    """Cross-workflow relationship explicitly separating deterministic signals from LLM reasoning."""
    workflow_a_id: str
    workflow_a_name: str
    workflow_b_id: str
    workflow_b_name: str
    relationship_type: str  # STRUCTURAL_SIMILARITY | SEMANTIC_SIMILARITY | SHARED_SOURCE | SHARED_TARGET | SHARED_LOGIC | OVERLAPPING_PIPELINE | DUPLICATE_CANDIDATE
    deterministic_signals: DeterministicSignals
    llm_reasoning: str = ""
    confidence: str = "HIGH"  # HIGH | MEDIUM | LOW
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_a_id": self.workflow_a_id,
            "workflow_a_name": self.workflow_a_name,
            "workflow_b_id": self.workflow_b_id,
            "workflow_b_name": self.workflow_b_name,
            "relationship_type": self.relationship_type,
            "deterministic_signals": self.deterministic_signals.to_dict(),
            "llm_reasoning": self.llm_reasoning,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class DeterministicMetrics:
    source_overlap: float = 0.0
    target_overlap: float = 0.0
    transformation_similarity: float = 0.0
    schema_similarity: float = 0.0
    grain_similarity: float = 0.0
    dag_similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_overlap": round(self.source_overlap, 3),
            "target_overlap": round(self.target_overlap, 3),
            "transformation_similarity": round(self.transformation_similarity, 3),
            "schema_similarity": round(self.schema_similarity, 3),
            "grain_similarity": round(self.grain_similarity, 3),
            "dag_similarity": round(self.dag_similarity, 3),
        }


@dataclass
class RiskContext:
    complexity_by_workflow: dict[str, str] = field(default_factory=dict)
    criticality_by_workflow: dict[str, str] = field(default_factory=dict)
    risk_level: str = "LOW"  # HIGH | MEDIUM | LOW
    risk_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity_by_workflow": self.complexity_by_workflow,
            "criticality_by_workflow": self.criticality_by_workflow,
            "risk_level": self.risk_level,
            "risk_notes": self.risk_notes,
        }


@dataclass
class OutputEvidence:
    production_targets: dict[str, list[str]] = field(default_factory=dict)
    inspection_sinks: dict[str, list[str]] = field(default_factory=dict)
    output_schemas: dict[str, list[str]] = field(default_factory=dict)
    output_grains: dict[str, list[str]] = field(default_factory=dict)
    is_equivalent_target: bool = False
    is_equivalent_schema: bool = False
    is_equivalent_grain: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "production_targets": self.production_targets,
            "inspection_sinks": self.inspection_sinks,
            "output_schemas": self.output_schemas,
            "output_grains": self.output_grains,
            "is_equivalent_target": self.is_equivalent_target,
            "is_equivalent_schema": self.is_equivalent_schema,
            "is_equivalent_grain": self.is_equivalent_grain,
        }


@dataclass
class DependencyEvidence:
    downstream_consumers: dict[str, list[str]] = field(default_factory=dict)
    upstream_producers: dict[str, list[str]] = field(default_factory=dict)
    shared_sources: list[str] = field(default_factory=list)
    shared_targets: list[str] = field(default_factory=list)
    dependency_status: str = "NOT_FOUND_IN_PORTFOLIO"  # KNOWN | NOT_FOUND_IN_PORTFOLIO | NOT_DETERMINABLE
    dependency_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "downstream_consumers": self.downstream_consumers,
            "upstream_producers": self.upstream_producers,
            "shared_sources": self.shared_sources,
            "shared_targets": self.shared_targets,
            "dependency_status": self.dependency_status,
            "dependency_notes": self.dependency_notes,
        }


@dataclass
class WorkflowFingerprint:
    """Deterministic structural and semantic fingerprint of a single workflow."""
    workflow_id: str
    workflow_name: str
    sources: list[str] = field(default_factory=list)
    source_types: dict[str, str] = field(default_factory=dict)
    source_fields: dict[str, list[str]] = field(default_factory=dict)
    production_targets: list[str] = field(default_factory=list)
    inspection_sinks: list[str] = field(default_factory=list)
    output_schemas: dict[str, list[str]] = field(default_factory=dict)
    output_grain: list[str] = field(default_factory=list)
    tool_types: list[str] = field(default_factory=list)
    transformation_signatures: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    join_keys: list[str] = field(default_factory=list)
    aggregations: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    has_python: bool = False
    has_r: bool = False
    has_macros: bool = False
    node_count: int = 0
    edge_count: int = 0
    dag_depth: int = 0
    branch_points: int = 0
    merge_points: int = 0
    topological_sequence: list[str] = field(default_factory=list)
    complexity_level: str = "LOW"
    complexity_score: float = 0.0
    criticality_level: str = "LOW"
    criticality_score: float = 0.0
    downstream_consumers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "sources": self.sources,
            "source_types": self.source_types,
            "source_fields": self.source_fields,
            "production_targets": self.production_targets,
            "inspection_sinks": self.inspection_sinks,
            "output_schemas": self.output_schemas,
            "output_grain": self.output_grain,
            "tool_types": self.tool_types,
            "transformation_signatures": self.transformation_signatures,
            "filters": self.filters,
            "join_keys": self.join_keys,
            "aggregations": self.aggregations,
            "formulas": self.formulas,
            "has_python": self.has_python,
            "has_r": self.has_r,
            "has_macros": self.has_macros,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "dag_depth": self.dag_depth,
            "branch_points": self.branch_points,
            "merge_points": self.merge_points,
            "topological_sequence": self.topological_sequence,
            "complexity_level": self.complexity_level,
            "complexity_score": self.complexity_score,
            "criticality_level": self.criticality_level,
            "criticality_score": self.criticality_score,
            "downstream_consumers": self.downstream_consumers,
        }


@dataclass
class WorkflowComparisonEvidence:
    """Pairwise cross-workflow deterministic comparison evidence."""
    workflow_a_id: str
    workflow_a_name: str
    workflow_b_id: str
    workflow_b_name: str
    metrics: DeterministicMetrics
    shared_logic: list[str] = field(default_factory=list)
    unique_a: list[str] = field(default_factory=list)
    unique_b: list[str] = field(default_factory=list)
    shared_sources: list[str] = field(default_factory=list)
    shared_targets: list[str] = field(default_factory=list)
    distinct_targets_a: list[str] = field(default_factory=list)
    distinct_targets_b: list[str] = field(default_factory=list)
    schema_differences: list[str] = field(default_factory=list)
    grain_differences: list[str] = field(default_factory=list)
    dependency_evidence: DependencyEvidence = field(default_factory=DependencyEvidence)
    opportunity_score: float = 0.0
    confidence: str = "HIGH"

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_a_id": self.workflow_a_id,
            "workflow_a_name": self.workflow_a_name,
            "workflow_b_id": self.workflow_b_id,
            "workflow_b_name": self.workflow_b_name,
            "metrics": self.metrics.to_dict(),
            "shared_logic": self.shared_logic,
            "unique_a": self.unique_a,
            "unique_b": self.unique_b,
            "shared_sources": self.shared_sources,
            "shared_targets": self.shared_targets,
            "distinct_targets_a": self.distinct_targets_a,
            "distinct_targets_b": self.distinct_targets_b,
            "schema_differences": self.schema_differences,
            "grain_differences": self.grain_differences,
            "dependency_evidence": self.dependency_evidence.to_dict(),
            "opportunity_score": round(self.opportunity_score, 1),
            "confidence": self.confidence,
        }


@dataclass
class RationalisationCandidate:
    """ETL Rationalisation candidate recommendation derived from deterministic signals and LLM qualification."""
    workflow_ids: list[str]
    workflow_names: list[str]
    recommendation_type: str  # CONSOLIDATE | RETIRE_CANDIDATE | SHARED_LOGIC | REVIEW
    candidate_id: str = ""
    reasoning: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: str = "HIGH"  # HIGH | MEDIUM | LOW
    opportunity_score: float = 0.0
    shared_logic: list[str] = field(default_factory=list)
    unique_functionality: dict[str, list[str]] = field(default_factory=dict)
    proposed_strategy: str = ""
    validation_requirements: list[str] = field(default_factory=list)
    deterministic_metrics: DeterministicMetrics = field(default_factory=DeterministicMetrics)
    output_evidence: OutputEvidence = field(default_factory=OutputEvidence)
    dependency_evidence: DependencyEvidence = field(default_factory=DependencyEvidence)
    risk_context: RiskContext = field(default_factory=RiskContext)
    admissible_recommendations: list[str] = field(default_factory=list)
    llm_enrichment_status: str = "DETERMINISTIC_BASELINE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id or f"cand_{'_'.join(self.workflow_ids)}",
            "workflow_ids": self.workflow_ids,
            "workflow_names": self.workflow_names,
            "recommendation_type": self.recommendation_type,
            "confidence": self.confidence,
            "opportunity_score": round(self.opportunity_score, 1),
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "shared_logic": self.shared_logic,
            "unique_functionality": self.unique_functionality,
            "proposed_strategy": self.proposed_strategy,
            "validation_requirements": self.validation_requirements,
            "deterministic_metrics": self.deterministic_metrics.to_dict() if hasattr(self.deterministic_metrics, "to_dict") else self.deterministic_metrics,
            "output_evidence": self.output_evidence.to_dict() if hasattr(self.output_evidence, "to_dict") else self.output_evidence,
            "dependency_evidence": self.dependency_evidence.to_dict() if hasattr(self.dependency_evidence, "to_dict") else self.dependency_evidence,
            "risk_context": self.risk_context.to_dict() if hasattr(self.risk_context, "to_dict") else self.risk_context,
            "admissible_recommendations": self.admissible_recommendations,
            "llm_enrichment_status": self.llm_enrichment_status,
        }


@dataclass
class RationalisationAnalysis:
    """Full rationalisation analysis response across the portfolio."""
    portfolio_id: str
    candidates: list[RationalisationCandidate] = field(default_factory=list)
    total_opportunities: int = 0
    recommendation_counts: dict[str, int] = field(default_factory=dict)
    analysed_workflow_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "candidates": [c.to_dict() for c in self.candidates],
            "total_opportunities": self.total_opportunities,
            "recommendation_counts": self.recommendation_counts,
            "analysed_workflow_count": self.analysed_workflow_count,
        }


@dataclass
class SharedDataset:
    """A dataset (source or target) referenced across multiple workflows."""
    dataset_name: str
    dataset_type: str  # "SOURCE" | "TARGET"
    workflow_ids: list[str]
    workflow_names: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "dataset_type": self.dataset_type,
            "workflow_ids": self.workflow_ids,
            "workflow_names": self.workflow_names,
        }


@dataclass
class PortfolioAggregateMetrics:
    """Deterministic aggregate statistics across the entire portfolio."""
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
    tool_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_workflows": self.total_workflows,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "total_tools": self.total_tools,
            "total_sources": self.total_sources,
            "unique_sources": self.unique_sources,
            "total_targets": self.total_targets,
            "unique_targets": self.unique_targets,
            "shared_sources_count": self.shared_sources_count,
            "shared_targets_count": self.shared_targets_count,
            "inspection_sinks_count": self.inspection_sinks_count,
            "tool_distribution": self.tool_distribution,
        }


@dataclass
class PortfolioAnalysis:
    """The authoritative result of a Multi-Workflow Portfolio Analysis."""
    portfolio_id: str
    portfolio_name: str
    workflow_count: int
    workflows: list[PortfolioWorkflowSummary]
    metrics: PortfolioAggregateMetrics
    shared_sources: list[SharedDataset]
    shared_targets: list[SharedDataset]
    relationships: list[WorkflowRelationship]
    rationalisation_candidates: list[RationalisationCandidate]
    business_area_counts: dict[str, int] = field(default_factory=dict)
    business_area_descriptions: dict[str, str] = field(default_factory=dict)
    business_areas: list[BusinessAreaGroup] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "workflow_count": self.workflow_count,
            "workflows": [w.to_dict() for w in self.workflows],
            "metrics": self.metrics.to_dict(),
            "shared_sources": [s.to_dict() for s in self.shared_sources],
            "shared_targets": [t.to_dict() for t in self.shared_targets],
            "relationships": [r.to_dict() for r in self.relationships],
            "rationalisation_candidates": [c.to_dict() for c in self.rationalisation_candidates],
            "business_area_counts": self.business_area_counts,
            "business_area_descriptions": self.business_area_descriptions,
            "business_areas": [ba.to_dict() for ba in self.business_areas],
            "created_at": self.created_at,
        }
