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

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
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
class RationalisationCandidate:
    """ETL Rationalisation candidate recommendation derived from deterministic signals and LLM qualification."""
    workflow_ids: list[str]
    workflow_names: list[str]
    recommendation_type: str  # CONSOLIDATE | RETIRE_CANDIDATE | SHARED_LOGIC | REVIEW
    reasoning: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: str = "HIGH"  # HIGH | MEDIUM | LOW

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_ids": self.workflow_ids,
            "workflow_names": self.workflow_names,
            "recommendation_type": self.recommendation_type,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "confidence": self.confidence,
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
            "created_at": self.created_at,
        }
