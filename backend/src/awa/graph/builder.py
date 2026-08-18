"""Workflow graph construction and analysis.

Builds a networkx DiGraph from the Workflow IR, with tools as nodes
and connections as edges. Provides topological ordering and
branch consumption analysis.
"""

from __future__ import annotations

import networkx as nx

from awa.model.workflow import Workflow
from awa.model.connection import Connection


class CyclicWorkflowError(Exception):
    """Raised when a workflow contains cycles."""
    pass


def build_graph(workflow: Workflow) -> nx.DiGraph:
    """Build a directed graph from the workflow IR.

    Nodes are tool IDs. Edges carry connection metadata
    (origin_anchor, destination_anchor).

    Args:
        workflow: Parsed Workflow IR.

    Returns:
        networkx DiGraph.

    Raises:
        CyclicWorkflowError: If the workflow contains cycles.
    """
    g = nx.DiGraph()

    for tool_id, tool in workflow.tools.items():
        g.add_node(tool_id, tool=tool)

    for conn in workflow.connections:
        if conn.origin_tool_id in workflow.tools and conn.destination_tool_id in workflow.tools:
            g.add_edge(
                conn.origin_tool_id,
                conn.destination_tool_id,
                origin_anchor=conn.origin_anchor,
                destination_anchor=conn.destination_anchor,
            )

    if not nx.is_directed_acyclic_graph(g):
        cycles = list(nx.simple_cycles(g))
        raise CyclicWorkflowError(f"Workflow contains cycles: {cycles}")

    return g


def execution_order(g: nx.DiGraph) -> list[int]:
    """Return tool IDs in topological (execution) order.

    This is the correct data-flow order derived from graph connectivity.
    Tool IDs are NOT execution order.
    """
    return list(nx.topological_sort(g))


def consumed_anchors(workflow: Workflow) -> dict[int, set[str]]:
    """Determine which output anchors of each tool are actually consumed.

    An anchor is consumed if at least one connection uses it as an origin.
    This is used to generate Python code only for consumed branches (C3).

    Returns:
        dict mapping tool_id to set of consumed anchor names.
    """
    consumed: dict[int, set[str]] = {}
    for conn in workflow.connections:
        consumed.setdefault(conn.origin_tool_id, set()).add(conn.origin_anchor)
    return consumed


def build_input_map(workflow: Workflow) -> dict[int, list[str]]:
    """For each tool, compute which DataFrame variable names feed into it.

    For dual-input tools (Join), inputs are ordered [left, right]
    based on destination_anchor.

    Returns:
        dict mapping tool_id to list of input variable names.
    """
    _LEFT_ANCHORS = {"left", "find", "targets", "f", "#1"}
    _RIGHT_ANCHORS = {"right", "replace", "source", "r", "s", "#2"}

    # First pass: collect inputs with anchor info
    raw_inputs: dict[int, list[tuple[str, str]]] = {}
    for conn in workflow.connections:
        df_name = resolve_output_variable(conn.origin_tool_id, conn.origin_anchor)
        raw_inputs.setdefault(conn.destination_tool_id, []).append(
            (df_name, conn.destination_anchor)
        )

    # Second pass: order inputs for dual-input tools
    input_map: dict[int, list[str]] = {}
    for tool_id, inputs in raw_inputs.items():
        tool = workflow.tools.get(tool_id)
        if tool and tool.tool_type in ("Join", "FindReplace", "AppendFields") and len(inputs) >= 2:
            left_dfs = [df for df, anchor in inputs if anchor.lower() in _LEFT_ANCHORS]
            right_dfs = [df for df, anchor in inputs if anchor.lower() in _RIGHT_ANCHORS]
            other_dfs = [
                df for df, anchor in inputs
                if anchor.lower() not in _LEFT_ANCHORS
                and anchor.lower() not in _RIGHT_ANCHORS
            ]
            input_map[tool_id] = left_dfs + right_dfs + other_dfs
        else:
            input_map[tool_id] = [df for df, _ in inputs]

    return input_map


def resolve_output_variable(tool_id: int, anchor: str) -> str:
    """Derive the DataFrame variable name from a tool ID and output anchor.

    Multi-output tools use anchor-specific suffixes:
    - Filter: True/False → _true/_false
    - Unique: Unique/Duplicates → _unique/_duplicates
    - Join: Join/Left/Right → _joined/_left_only/_right_only
    """
    a = anchor.lower()
    if a in ("true",):
        return f"df_{tool_id}_true"
    elif a in ("false",):
        return f"df_{tool_id}_false"
    elif a in ("unique", "u"):
        return f"df_{tool_id}_unique"
    elif a in ("duplicates", "d"):
        return f"df_{tool_id}_duplicates"
    elif a in ("join", "j"):
        return f"df_{tool_id}_joined"
    elif a in ("left", "l"):
        return f"df_{tool_id}_left_only"
    elif a in ("right", "r"):
        return f"df_{tool_id}_right_only"
    else:
        return f"df_{tool_id}"
