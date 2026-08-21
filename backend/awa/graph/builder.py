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


import heapq

def execution_order(g: nx.DiGraph) -> list[int]:
    """Return tool IDs in deterministic topological (execution) order.

    Every upstream dependency appears before its downstream node.
    Independent branches are ordered deterministically by tool ID using Kahn's algorithm.
    Explicitly detects cycles.
    """
    if not nx.is_directed_acyclic_graph(g):
        cycles = list(nx.simple_cycles(g))
        raise CyclicWorkflowError(f"Workflow contains cycles: {cycles}")

    in_degree = dict(g.in_degree())
    ready: list[int] = [n for n, deg in in_degree.items() if deg == 0]
    heapq.heapify(ready)

    order: list[int] = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for succ in sorted(g.successors(node)):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                heapq.heappush(ready, succ)

    if len(order) != len(g.nodes):
        raise CyclicWorkflowError("Cycle detected during topological sort")

    return order


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


def build_input_map(
    workflow: Workflow,
    stream_env: dict[tuple[int, str], str] | None = None,
) -> dict[int, list[str]]:
    """For each tool, compute which DataFrame variable names feed into it.

    For dual-input tools (Join), inputs are ordered [left, right]
    based on destination_anchor.

    Args:
        workflow: Parsed Workflow IR.
        stream_env: Optional mapping of (origin_tool_id, origin_anchor) -> dataframe_variable.

    Returns:
        dict mapping tool_id to list of input variable names.
    """
    _LEFT_ANCHORS = {"left", "find", "targets", "f", "#1"}
    _RIGHT_ANCHORS = {"right", "replace", "source", "r", "s", "#2"}

    env = stream_env or {}

    # First pass: collect inputs with anchor info
    raw_inputs: dict[int, list[tuple[str, str]]] = {}
    for conn in workflow.connections:
        orig_tid = conn.origin_tool_id
        orig_anchor = (conn.origin_anchor or "").lower()
        
        # Look up variable in stream_env, falling back to resolve_output_variable
        df_name = (
            env.get((orig_tid, orig_anchor))
            or env.get((orig_tid, "output"))
            or env.get((orig_tid, ""))
            or resolve_output_variable(orig_tid, conn.origin_anchor)
        )
        raw_inputs.setdefault(conn.destination_tool_id, []).append(
            (df_name, (conn.destination_anchor or "").lower())
        )

    # Second pass: order inputs for dual-input tools
    input_map: dict[int, list[str]] = {}
    for tool_id, inputs in raw_inputs.items():
        tool = workflow.tools.get(tool_id)
        if tool and tool.tool_type in ("Join", "FindReplace", "AppendFields") and len(inputs) >= 2:
            left_dfs = [df for df, anchor in inputs if anchor in _LEFT_ANCHORS]
            right_dfs = [df for df, anchor in inputs if anchor in _RIGHT_ANCHORS]
            other_dfs = [
                df for df, anchor in inputs
                if anchor not in _LEFT_ANCHORS
                and anchor not in _RIGHT_ANCHORS
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
    a = anchor.lower() if anchor else ""
    if a in ("true", "t"):
        return f"df_{tool_id}_true"
    elif a in ("false", "f"):
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
