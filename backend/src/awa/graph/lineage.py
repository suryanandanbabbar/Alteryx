"""Data lineage tracking.

Builds lineage paths through the workflow graph.
Field-level lineage is a future extension.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field

import networkx as nx

from backend.src.awa.model.workflow import Workflow


@dataclass
class LineagePath:
    """A data lineage path from source to sink."""
    tool_ids: list[int] = dc_field(default_factory=list)
    tool_types: list[str] = dc_field(default_factory=list)
    tool_names: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tool_ids": self.tool_ids,
            "tool_types": self.tool_types,
            "tool_names": self.tool_names,
        }


def compute_lineage_paths(
    workflow: Workflow,
    g: nx.DiGraph,
) -> list[LineagePath]:
    """Compute all source-to-sink lineage paths.

    Returns a list of LineagePath objects, each representing a
    complete data flow from an input tool to an output tool.
    """
    sources = [n for n in g.nodes() if g.in_degree(n) == 0]
    sinks = [n for n in g.nodes() if g.out_degree(n) == 0]

    paths: list[LineagePath] = []
    for source in sorted(sources):
        for sink in sorted(sinks):
            try:
                for path_ids in nx.all_simple_paths(g, source, sink):
                    lp = LineagePath(
                        tool_ids=list(path_ids),
                        tool_types=[
                            workflow.tools[tid].tool_type
                            for tid in path_ids
                            if tid in workflow.tools
                        ],
                        tool_names=[
                            workflow.tools[tid].name or f"Tool {tid}"
                            for tid in path_ids
                            if tid in workflow.tools
                        ],
                    )
                    paths.append(lp)
            except nx.NodeNotFound:
                continue

    return paths
