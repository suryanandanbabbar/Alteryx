"""Format-independent documentation model.

Separates documentation content from rendering format (DOCX/MD).
This ensures the core engine never directly depends on python-docx.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from backend.src.awa.model.dag_layout import DagLayout
from backend.src.awa.model.diagnostic import Dependency, Diagnostic
from backend.src.awa.graph.lineage import LineagePath


@dataclass
class NodeDocEntry:
    """Documentation entry for a single workflow tool/node."""
    tool_id: int
    tool_type: str
    name: str
    plugin: str
    support_level: str
    annotation: str
    description: str
    configuration: dict[str, Any] = dc_field(default_factory=dict)
    input_variables: list[str] = dc_field(default_factory=list)
    output_variables: dict[str, str] = dc_field(default_factory=dict)
    diagnostics: list[Diagnostic] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "tool_type": self.tool_type,
            "name": self.name,
            "plugin": self.plugin,
            "support_level": self.support_level,
            "annotation": self.annotation,
            "description": self.description,
            "configuration": self.configuration,
            "input_variables": self.input_variables,
            "output_variables": self.output_variables,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class ExecutionStepDocEntry:
    """Execution step entry for the documentation."""
    step_number: int
    tool_id: int
    tool_type: str
    name: str
    visual_category: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_number": self.step_number,
            "tool_id": self.tool_id,
            "tool_type": self.tool_type,
            "name": self.name,
            "visual_category": self.visual_category,
        }


@dataclass
class DocumentModel:
    """Complete format-independent documentation model.

    Renderers (such as docx_generator) consume this model to produce
    output files without needing access to raw workflow internals.
    """
    title: str
    metadata: dict[str, str]
    metrics: dict[str, int]
    execution_order: list[ExecutionStepDocEntry]
    dag_layout: DagLayout
    nodes: list[NodeDocEntry]
    lineage_paths: list[LineagePath]
    python_summary: str
    dependencies: list[Dependency]
    diagnostics: list[Diagnostic]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "metadata": self.metadata,
            "metrics": self.metrics,
            "execution_order": [s.to_dict() for s in self.execution_order],
            "dag_layout": self.dag_layout.to_dict(),
            "nodes": [n.to_dict() for n in self.nodes],
            "lineage_paths": [lp.to_dict() for lp in self.lineage_paths],
            "python_summary": self.python_summary,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
