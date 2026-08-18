"""DAG Layout algorithm.

Calculates exact 2D coordinates for nodes and routes edges for graph visualization.
The output DagLayout is the single source of truth for:
- Standalone SVG generator
- React interactive DAG viewer
- DOCX embedded diagram image
"""

from __future__ import annotations

import networkx as nx

from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.dag_layout import DagLayout, DagNodeLayout, DagEdgeLayout
from backend.src.awa.model.visual_category import get_visual_category


# Layout geometry constants
NODE_WIDTH = 170.0
NODE_HEIGHT = 65.0
HORIZONTAL_GAP = 70.0
VERTICAL_GAP = 50.0
PADDING_X = 60.0
PADDING_Y = 60.0


def compute_dag_layout(
    graph: nx.DiGraph,
    workflow: Workflow,
    execution_order: list[int],
) -> DagLayout:
    """Compute deterministic (x, y) coordinates for all nodes and route edges.

    Uses topological layering:
    - Layer (column) = longest path distance from any root node
    - Row (within column) = assigned to balance and prevent overlap
    - Edges = connected from (x + width, y + height/2) of source to (x, y + height/2) of target

    Args:
        graph: NetworkX DiGraph of the workflow.
        workflow: Canonical Workflow IR.
        execution_order: Tool IDs in topological execution order.

    Returns:
        Canonical DagLayout with positioned nodes and routed edges.
    """
    if not graph.nodes:
        return DagLayout(
            nodes=[],
            edges=[],
            width=300.0,
            height=150.0,
            title=workflow.metadata.name or "Workflow DAG",
        )

    # 1. Compute layer (rank) for each node based on longest path from roots
    layers: dict[int, int] = {}
    
    # Initialize roots with layer 0
    for node in graph.nodes:
        if graph.in_degree(node) == 0:
            layers[node] = 0

    # Forward pass in topological order to determine max layer
    for node in execution_order:
        current_layer = layers.get(node, 0)
        for succ in graph.successors(node):
            layers[succ] = max(layers.get(succ, 0), current_layer + 1)

    # Group nodes by layer
    layer_nodes: dict[int, list[int]] = {}
    for node in execution_order:
        lvl = layers.get(node, 0)
        layer_nodes.setdefault(lvl, []).append(node)

    # Sort layers
    max_layer = max(layers.values()) if layers else 0
    max_nodes_in_layer = max((len(nodes) for nodes in layer_nodes.values()), default=1)

    total_width = PADDING_X * 2 + (max_layer + 1) * NODE_WIDTH + max_layer * HORIZONTAL_GAP
    total_height = PADDING_Y * 2 + max_nodes_in_layer * NODE_HEIGHT + (max_nodes_in_layer - 1) * VERTICAL_GAP
    total_height = max(total_height, 220.0)

    # 2. Position nodes
    positioned_nodes: dict[int, DagNodeLayout] = {}

    for lvl, nodes in layer_nodes.items():
        col_x = PADDING_X + lvl * (NODE_WIDTH + HORIZONTAL_GAP)
        col_height = len(nodes) * NODE_HEIGHT + (len(nodes) - 1) * VERTICAL_GAP
        start_y = (total_height - col_height) / 2.0  # vertically center the column

        for idx, node_id in enumerate(nodes):
            node_y = start_y + idx * (NODE_HEIGHT + VERTICAL_GAP)
            tool = workflow.tools.get(node_id)
            tool_type = tool.tool_type if tool else "Unknown"
            name = tool.name if (tool and tool.name) else tool_type
            vcat = get_visual_category(tool_type)

            exec_idx = execution_order.index(node_id) if node_id in execution_order else 0

            layout_node = DagNodeLayout(
                tool_id=node_id,
                x=col_x,
                y=node_y,
                width=NODE_WIDTH,
                height=NODE_HEIGHT,
                label=name,
                tool_type=tool_type,
                execution_index=exec_idx,
                visual_category=vcat,
            )
            positioned_nodes[node_id] = layout_node

    # 3. Route edges between nodes
    edges: list[DagEdgeLayout] = []
    for conn in workflow.connections:
        src_id = conn.origin_tool_id
        dst_id = conn.destination_tool_id

        src_node = positioned_nodes.get(src_id)
        dst_node = positioned_nodes.get(dst_id)

        if src_node and dst_node:
            src_x = src_node.x + src_node.width
            src_y = src_node.y + src_node.height / 2.0
            dst_x = dst_node.x
            dst_y = dst_node.y + dst_node.height / 2.0

            # Waypoints: source -> mid1 -> mid2 -> destination for smooth s-curves
            dx = (dst_x - src_x) / 2.0
            points = [
                (src_x, src_y),
                (src_x + dx, src_y),
                (dst_x - dx, dst_y),
                (dst_x, dst_y),
            ]

            edges.append(
                DagEdgeLayout(
                    source_id=src_id,
                    target_id=dst_id,
                    source_anchor=conn.origin_anchor,
                    target_anchor=conn.destination_anchor,
                    path_points=points,
                )
            )

    return DagLayout(
        nodes=list(positioned_nodes.values()),
        edges=edges,
        width=total_width,
        height=total_height,
        title=workflow.metadata.name or "Workflow DAG",
    )
