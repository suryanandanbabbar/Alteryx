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
    input_node_ids: list[int] = dc_field(default_factory=list)
    output_node_ids: list[int] = dc_field(default_factory=list)
    support_summary: dict[str, int] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "total_connections": self.total_connections,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "input_node_ids": self.input_node_ids,
            "output_node_ids": self.output_node_ids,
            "support_summary": self.support_summary,
        }


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

    def to_dict(self) -> dict[str, Any]:
        """Convert the entire canonical result to a comprehensive dictionary."""
        return {
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
        }
