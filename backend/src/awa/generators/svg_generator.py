"""Deterministic SVG generator for Alteryx Workflow DAGs.

Generates standalone, scalable vector SVG from canonical DagLayout.
Contains real vector elements (<svg>, <g>, <rect>, <text>, <path>, <marker>)
matching the application's visual design.
"""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET

from backend.src.awa.model.dag_layout import DagLayout
from backend.src.awa.model.visual_category import get_category_colors, CATEGORY_COLORS


def generate_svg(layout: DagLayout, custom_colors: dict[str, dict[str, str]] | None = None) -> str:
    """Generate a clean, standalone vector SVG string from a DagLayout.

    Args:
        layout: Canonical DAG layout with node positions and edge waypoints.
        custom_colors: Optional override for visual category colors.

    Returns:
        Valid SVG XML string.
    """
    colors = custom_colors or CATEGORY_COLORS

    width = max(layout.width, 400.0)
    height = max(layout.height + 60.0, 260.0)  # +60 for title bar

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "viewBox": f"0 0 {width} {height}",
            "width": "100%",
            "height": "100%",
            "style": "background: #0d1326; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;",
        },
    )

    # 1. Defs: Markers, Gradients, Filters
    defs = ET.SubElement(svg, "defs")

    # Arrowhead marker
    marker = ET.SubElement(
        defs,
        "marker",
        {
            "id": "arrow",
            "viewBox": "0 0 10 10",
            "refX": "8",
            "refY": "5",
            "markerWidth": "6",
            "markerHeight": "6",
            "orient": "auto-start-reverse",
        },
    )
    ET.SubElement(
        marker,
        "path",
        {
            "d": "M 0 1 L 10 5 L 0 9 z",
            "fill": "#64748b",
        },
    )

    # Labeled arrowhead marker (for branches like True/False)
    marker_active = ET.SubElement(
        defs,
        "marker",
        {
            "id": "arrow-active",
            "viewBox": "0 0 10 10",
            "refX": "8",
            "refY": "5",
            "markerWidth": "6",
            "markerHeight": "6",
            "orient": "auto-start-reverse",
        },
    )
    ET.SubElement(
        marker_active,
        "path",
        {
            "d": "M 0 1 L 10 5 L 0 9 z",
            "fill": "#38bdf8",
        },
    )

    # 2. Header / Title Bar
    header_g = ET.SubElement(svg, "g", {"id": "header", "transform": "translate(20, 28)"})
    title_text = ET.SubElement(
        header_g,
        "text",
        {
            "x": "0",
            "y": "0",
            "fill": "#f8fafc",
            "font-size": "15",
            "font-weight": "600",
            "letter-spacing": "0.5px",
        },
    )
    title_text.text = f"Alteryx Workflow DAG — {html.escape(layout.title)}"

    subtitle_text = ET.SubElement(
        header_g,
        "text",
        {
            "x": "0",
            "y": "18",
            "fill": "#64748b",
            "font-size": "11",
            "font-weight": "400",
        },
    )
    subtitle_text.text = f"{len(layout.nodes)} nodes · {len(layout.edges)} connections"

    # Main graph content group (offset by title bar height)
    graph_g = ET.SubElement(svg, "g", {"id": "graph", "transform": "translate(0, 45)"})

    # 3. Render Edges
    edges_g = ET.SubElement(graph_g, "g", {"id": "edges"})
    for edge in layout.edges:
        if not edge.path_points:
            continue

        # Build cubic bezier curve path: M p0 C p1, p2, p3
        pts = edge.path_points
        if len(pts) >= 4:
            d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} C {pts[1][0]:.1f} {pts[1][1]:.1f}, {pts[2][0]:.1f} {pts[2][1]:.1f}, {pts[3][0]:.1f} {pts[3][1]:.1f}"
        else:
            d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} L {pts[-1][0]:.1f} {pts[-1][1]:.1f}"

        has_label = bool(edge.source_anchor and edge.source_anchor not in ("Output", "0", "#1"))
        edge_color = "#38bdf8" if has_label else "#475569"
        marker_id = "url(#arrow-active)" if has_label else "url(#arrow)"

        ET.SubElement(
            edges_g,
            "path",
            {
                "d": d,
                "fill": "none",
                "stroke": edge_color,
                "stroke-width": "2",
                "marker-end": marker_id,
                "opacity": "0.85",
            },
        )

        # Optional edge label
        if has_label and len(pts) >= 2:
            mid_x = (pts[0][0] + pts[-1][0]) / 2.0
            mid_y = (pts[0][1] + pts[-1][1]) / 2.0 - 6.0
            lbl_bg = ET.SubElement(
                edges_g,
                "rect",
                {
                    "x": f"{mid_x - 18:.1f}",
                    "y": f"{mid_y - 10:.1f}",
                    "width": "36",
                    "height": "14",
                    "rx": "3",
                    "fill": "#0f172a",
                    "stroke": "#334155",
                    "stroke-width": "1",
                },
            )
            lbl = ET.SubElement(
                edges_g,
                "text",
                {
                    "x": f"{mid_x:.1f}",
                    "y": f"{mid_y:.1f}",
                    "fill": "#38bdf8",
                    "font-size": "9",
                    "font-weight": "600",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
            lbl.text = edge.source_anchor

    # 4. Render Nodes
    nodes_g = ET.SubElement(graph_g, "g", {"id": "nodes"})
    for node in layout.nodes:
        cat_color = get_category_colors(node.visual_category)

        node_group = ET.SubElement(
            nodes_g,
            "g",
            {
                "id": f"node-{node.tool_id}",
                "transform": f"translate({node.x:.1f}, {node.y:.1f})",
                "style": "cursor: pointer;",
            },
        )

        # Outer rounded rectangle card
        ET.SubElement(
            node_group,
            "rect",
            {
                "width": f"{node.width:.1f}",
                "height": f"{node.height:.1f}",
                "rx": "8",
                "ry": "8",
                "fill": cat_color["fill"],
                "stroke": cat_color["stroke"],
                "stroke-width": "1.5",
            },
        )

        # Tool ID Badge (circle on left)
        circle_cx = 24.0
        circle_cy = node.height / 2.0
        ET.SubElement(
            node_group,
            "circle",
            {
                "cx": f"{circle_cx:.1f}",
                "cy": f"{circle_cy:.1f}",
                "r": "12",
                "fill": cat_color["stroke"],
            },
        )
        id_text = ET.SubElement(
            node_group,
            "text",
            {
                "x": f"{circle_cx:.1f}",
                "y": f"{circle_cy + 1:.1f}",
                "fill": "#0a0f1d",
                "font-size": "11",
                "font-weight": "bold",
                "text-anchor": "middle",
                "dominant-baseline": "middle",
            },
        )
        id_text.text = str(node.tool_id)

        # Tool Type Text
        type_text = ET.SubElement(
            node_group,
            "text",
            {
                "x": "44",
                "y": f"{circle_cy - 7:.1f}",
                "fill": cat_color["text"],
                "font-size": "12",
                "font-weight": "600",
            },
        )
        # Truncate type if too long
        type_display = node.tool_type if len(node.tool_type) <= 16 else node.tool_type[:14] + ".."
        type_text.text = type_display

        # Tool Name / Annotation Subtitle
        name_text = ET.SubElement(
            node_group,
            "text",
            {
                "x": "44",
                "y": f"{circle_cy + 11:.1f}",
                "fill": "#94a3b8",
                "font-size": "10",
                "font-weight": "400",
            },
        )
        label_display = node.label if len(node.label) <= 18 else node.label[:16] + ".."
        name_text.text = label_display

    return ET.tostring(svg, encoding="unicode")
