"""Graph traversal utilities for lineage and reachability."""

from __future__ import annotations

import networkx as nx


def ancestors(g: nx.DiGraph, tool_id: int) -> set[int]:
    """Return all upstream tool IDs that feed into a given tool."""
    return nx.ancestors(g, tool_id)


def descendants(g: nx.DiGraph, tool_id: int) -> set[int]:
    """Return all downstream tool IDs that receive from a given tool."""
    return nx.descendants(g, tool_id)


def source_tools(g: nx.DiGraph) -> list[int]:
    """Return tool IDs with no incoming edges (data sources)."""
    return [n for n in g.nodes() if g.in_degree(n) == 0]


def sink_tools(g: nx.DiGraph) -> list[int]:
    """Return tool IDs with no outgoing edges (terminal/output tools)."""
    return [n for n in g.nodes() if g.out_degree(n) == 0]


def disconnected_tools(g: nx.DiGraph) -> list[int]:
    """Return tool IDs with no connections at all."""
    return [n for n in g.nodes() if g.degree(n) == 0]
