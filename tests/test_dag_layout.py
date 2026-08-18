"""Tests for DAG layouter and SVG generator."""

import xml.etree.ElementTree as ET
import networkx as nx
import pytest

from backend.src.awa.parser.xml_parser import parse_workflow
from backend.src.awa.graph.builder import build_graph, execution_order
from backend.src.awa.graph.dag_layouter import compute_dag_layout
from backend.src.awa.generators.svg_generator import generate_svg


def test_dag_layouter_simple_filter():
    wf = parse_workflow("fixtures/basic/simple_filter.yxmd")
    g = build_graph(wf)
    order = execution_order(g)

    layout = compute_dag_layout(g, wf, order)
    assert len(layout.nodes) == len(wf.tools)
    assert len(layout.edges) == len(wf.connections)
    assert layout.width > 0
    assert layout.height > 0

    # Verify positions are distinct
    positions = [(n.x, n.y) for n in layout.nodes]
    assert len(positions) == len(set(positions))

    # Input node should be to the left of Filter node, which is to the left of Output node
    node_map = {n.tool_id: n for n in layout.nodes}
    assert node_map[1].x < node_map[2].x < node_map[3].x


def test_dag_layouter_join_workflow():
    wf = parse_workflow("fixtures/joins/join_workflow.yxmd")
    g = build_graph(wf)
    order = execution_order(g)

    layout = compute_dag_layout(g, wf, order)
    assert len(layout.nodes) == 6
    assert len(layout.edges) == 5

    # Dual inputs (Tool 1 & Tool 2) should be in layer 0 (same x coordinate)
    node_map = {n.tool_id: n for n in layout.nodes}
    assert node_map[1].x == node_map[2].x
    # But different y coordinates
    assert node_map[1].y != node_map[2].y


def test_svg_generator_valid_xml():
    wf = parse_workflow("fixtures/joins/join_workflow.yxmd")
    g = build_graph(wf)
    order = execution_order(g)
    layout = compute_dag_layout(g, wf, order)

    svg_str = generate_svg(layout)
    assert "<svg" in svg_str
    assert "</svg>" in svg_str

    # Must parse as valid XML
    root = ET.fromstring(svg_str)
    assert root.tag.endswith("svg")

    # Must contain nodes and paths
    nodes = root.findall(".//{http://www.w3.org/2000/svg}g[@id='nodes']/{http://www.w3.org/2000/svg}g")
    assert len(nodes) == 6

    paths = root.findall(".//{http://www.w3.org/2000/svg}g[@id='edges']/{http://www.w3.org/2000/svg}path")
    assert len(paths) == 5
