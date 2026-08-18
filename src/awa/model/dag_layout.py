"""DAG layout model — positioned nodes and routed edges for visualization.

This model is the SINGLE source of layout information.
It is computed once and consumed by:
- SVG generator (standalone artifact)
- React DAG viewer (interactive display)
- DOCX generator (embedded diagram image)

No component independently calculates graph layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


@dataclass
class DagNodeLayout:
    """Positioned node in the DAG visualization.

    Attributes:
        tool_id: Alteryx tool ID.
        x: Horizontal position (left edge of node).
        y: Vertical position (top edge of node).
        width: Node width in layout units.
        height: Node height in layout units.
        label: Display label (tool name or type).
        tool_type: Alteryx tool type string.
        execution_index: Position in execution order (0-based).
        visual_category: Category for color coding (from visual_category.py).
    """
    tool_id: int
    x: float
    y: float
    width: float
    height: float
    label: str
    tool_type: str
    execution_index: int
    visual_category: str

    def to_dict(self) -> dict:
        return {
            "tool_id": self.tool_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "label": self.label,
            "tool_type": self.tool_type,
            "execution_index": self.execution_index,
            "visual_category": self.visual_category,
        }


@dataclass
class DagEdgeLayout:
    """Routed edge in the DAG visualization.

    Attributes:
        source_id: Source tool ID.
        target_id: Target tool ID.
        source_anchor: Output anchor name on source tool.
        target_anchor: Input anchor name on target tool.
        path_points: List of (x, y) waypoints for the edge path.
    """
    source_id: int
    target_id: int
    source_anchor: str
    target_anchor: str
    path_points: list[tuple[float, float]] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "source_anchor": self.source_anchor,
            "target_anchor": self.target_anchor,
            "path_points": [{"x": p[0], "y": p[1]} for p in self.path_points],
        }


@dataclass
class DagLayout:
    """Complete DAG layout with positioned nodes and routed edges.

    This is the canonical layout model. All visualization components
    (SVG, React, DOCX) derive from this single representation.

    Attributes:
        nodes: Positioned node layout entries.
        edges: Routed edge layout entries.
        width: Total layout width.
        height: Total layout height.
        title: Diagram title (typically workflow name).
    """
    nodes: list[DagNodeLayout] = dc_field(default_factory=list)
    edges: list[DagEdgeLayout] = dc_field(default_factory=list)
    width: float = 0.0
    height: float = 0.0
    title: str = ""

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "width": self.width,
            "height": self.height,
            "title": self.title,
        }

    def get_node(self, tool_id: int) -> DagNodeLayout | None:
        """Look up the node layout for a given tool ID."""
        for node in self.nodes:
            if node.tool_id == tool_id:
                return node
        return None
