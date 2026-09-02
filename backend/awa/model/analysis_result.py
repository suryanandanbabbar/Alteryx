"""Canonical Analysis Result — single source of truth for the entire application.

Every output generator, API endpoint, and UI view derives directly from
this model. No component independently re-evaluates or re-calculates
graph structure, metrics, or translation outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any
import networkx as nx

from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.diagnostic import Diagnostic
from awa.model.source_info import SourceInfo
from awa.model.dag_layout import DagLayout
from awa.model.python_trace import PythonTraceMap, ToolExplanation
from awa.graph.lineage import LineagePath


@dataclass
class WorkflowMetrics:
    """Core metrics derived from the workflow and graph."""
    total_nodes: int
    total_connections: int
    input_count: int
    output_count: int
    terminal_node_count: int = 0
    terminal_node_ids: list[int] = dc_field(default_factory=list)
    business_output_count: int = 0
    business_output_node_ids: list[int] = dc_field(default_factory=list)
    container_count: int = 0
    annotation_count: int = 0
    input_node_ids: list[int] = dc_field(default_factory=list)
    output_node_ids: list[int] = dc_field(default_factory=list)
    support_summary: dict[str, int] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "total_connections": self.total_connections,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "terminal_node_count": self.terminal_node_count,
            "terminal_node_ids": self.terminal_node_ids,
            "business_output_count": self.business_output_count,
            "business_output_node_ids": self.business_output_node_ids,
            "container_count": self.container_count,
            "annotation_count": self.annotation_count,
            "input_node_ids": self.input_node_ids,
            "output_node_ids": self.output_node_ids,
            "support_summary": self.support_summary,
        }


from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.sttm import STTMDocument


@dataclass
class CanonicalAnalysisResult:
    """The authoritative result of an Alteryx workflow analysis.

    All downstream artifacts and API representations derive strictly from here.
    """
    analysis_id: str
    source: SourceInfo
    workflow: Workflow
    graph: nx.DiGraph
    execution_order: list[int]
    translations: dict[int, TranslationResult]
    consumed_anchors: dict[int, set[str]]
    lineage_paths: list[LineagePath]
    metrics: WorkflowMetrics
    dag_layout: DagLayout
    python_trace: PythonTraceMap
    tool_explanations: dict[int, ToolExplanation]
    required_libraries: list[str]
    diagnostics: list[Diagnostic]
    business_summary: WorkflowBusinessSummary | None = None
    sttm: STTMDocument | None = None

    @property
    def business_purpose(self) -> str:
        """Canonical business purpose prose from business_summary."""
        return self.business_summary.business_purpose if self.business_summary else ""

    @property
    def business_function(self) -> str:
        """Canonical primary business function from business_summary."""
        return getattr(self.business_summary, "business_function", "") if self.business_summary else ""

    @property
    def business_area_tag(self) -> str:
        """Canonical business area tag from business_summary."""
        if self.business_summary and self.business_summary.business_area_tag:
            return self.business_summary.business_area_tag.strip()
        return ""

    @property
    def business_area_tag_source(self) -> str:
        """Canonical provenance source of business_area_tag ("llm" or "deterministic_fallback")."""
        return getattr(self.business_summary, "business_area_tag_source", "deterministic_fallback") if self.business_summary else "deterministic_fallback"

    @property
    def business_area_taxonomy_version(self) -> str:
        """Canonical taxonomy version of business area definitions."""
        return getattr(self.business_summary, "business_area_taxonomy_version", "3.0") if self.business_summary else "3.0"

    @property
    def classification_conflict(self) -> bool:
        """Whether a functional conflict was detected and resolved during classification."""
        return getattr(self.business_summary, "classification_conflict", False) if self.business_summary else False

    @property
    def classification_evidence(self) -> list[str]:
        """Auditable classification reasons and factors."""
        return getattr(self.business_summary, "classification_evidence", []) if self.business_summary else []

    @property
    def criticality_score(self) -> float:
        return getattr(self.business_summary, "criticality_score", 0.0) if self.business_summary else 0.0

    @property
    def criticality_level(self) -> str:
        return getattr(self.business_summary, "criticality_level", "LOW") if self.business_summary else "LOW"

    @property
    def criticality_justification(self) -> str:
        return getattr(self.business_summary, "criticality_justification", "") if self.business_summary else ""

    @property
    def criticality_business_consequence(self) -> str:
        return getattr(self.business_summary, "criticality_business_consequence", "") if self.business_summary else ""

    @property
    def criticality_dependency_impact(self) -> str:
        return getattr(self.business_summary, "criticality_dependency_impact", "") if self.business_summary else ""

    @property
    def criticality_affected_scope(self) -> str:
        return getattr(self.business_summary, "criticality_affected_scope", "") if self.business_summary else ""

    @property
    def criticality_migration_implication(self) -> str:
        return getattr(self.business_summary, "criticality_migration_implication", "") if self.business_summary else ""

    @property
    def criticality_source(self) -> str:
        return getattr(self.business_summary, "criticality_source", "deterministic_fallback") if self.business_summary else "deterministic_fallback"

    @property
    def criticality_factors(self) -> list[str]:
        return getattr(self.business_summary, "criticality_factors", []) if self.business_summary else []

    @property
    def factor_assessments(self) -> dict[str, Any]:
        return getattr(self.business_summary, "factor_assessments", {}) if self.business_summary else {}

    def to_dict(self) -> dict[str, Any]:
        """Convert the entire canonical result to a comprehensive dictionary."""
        d: dict[str, Any] = {
            "analysis_id": self.analysis_id,
            "source": self.source.to_dict(),
            "workflow": self.workflow.to_dict(),
            "execution_order": self.execution_order,
            "metrics": self.metrics.to_dict(),
            "dag_layout": self.dag_layout.to_dict(),
            "python_trace": self.python_trace.to_dict(),
            "tool_explanations": {
                str(k): v.to_dict() for k, v in self.tool_explanations.items()
            },
            "required_libraries": self.required_libraries,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "lineage_paths": [lp.to_dict() for lp in self.lineage_paths],
            "business_purpose": self.business_purpose,
            "business_function": self.business_function,
            "business_area_tag": self.business_area_tag,
            "business_area_tag_source": self.business_area_tag_source,
            "business_area_taxonomy_version": self.business_area_taxonomy_version,
            "classification_conflict": self.classification_conflict,
            "classification_evidence": self.classification_evidence,
            "criticality_score": self.criticality_score,
            "criticality_level": self.criticality_level,
            "criticality_justification": self.criticality_justification,
            "criticality_business_consequence": self.criticality_business_consequence,
            "criticality_dependency_impact": self.criticality_dependency_impact,
            "criticality_affected_scope": self.criticality_affected_scope,
            "criticality_migration_implication": self.criticality_migration_implication,
            "criticality_source": self.criticality_source,
            "criticality_factors": self.criticality_factors,
            "factor_assessments": self.factor_assessments,
        }
        if self.business_summary is not None:
            d["business_summary"] = self.business_summary.to_dict()
        if self.sttm is not None:
            d["sttm"] = self.sttm.to_dict()
        return d

