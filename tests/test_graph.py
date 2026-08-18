"""Graph tests — validates DAG construction and topological ordering."""

import pytest
from pathlib import Path

from awa.parser.xml_parser import parse_workflow
from awa.graph.builder import (
    build_graph,
    execution_order,
    consumed_anchors,
    build_input_map,
    resolve_output_variable,
)
from awa.graph.traversal import source_tools, sink_tools


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestSimpleFilterGraph:
    """Graph tests for simple_filter.yxmd (linear: 1→2→3)."""

    @pytest.fixture
    def graph_data(self):
        wf = parse_workflow(FIXTURES_DIR / "basic" / "simple_filter.yxmd")
        g = build_graph(wf)
        return wf, g

    def test_topological_order(self, graph_data):
        wf, g = graph_data
        order = execution_order(g)
        assert order == [1, 2, 3]

    def test_source_tools(self, graph_data):
        _, g = graph_data
        sources = source_tools(g)
        assert sources == [1]

    def test_sink_tools(self, graph_data):
        _, g = graph_data
        sinks = sink_tools(g)
        assert sinks == [3]

    def test_consumed_anchors(self, graph_data):
        wf, _ = graph_data
        consumed = consumed_anchors(wf)
        assert "Output" in consumed.get(1, set())
        assert "True" in consumed.get(2, set())
        # Tool 3 has no consumed outputs (it's a sink)
        assert 3 not in consumed or len(consumed[3]) == 0

    def test_input_map(self, graph_data):
        wf, _ = graph_data
        imap = build_input_map(wf)
        # Tool 2 (Filter) gets input from Tool 1
        assert imap[2] == ["df_1"]
        # Tool 3 (Output) gets input from Tool 2's True branch
        assert imap[3] == ["df_2_true"]


class TestJoinGraph:
    """Graph tests for join_workflow.yxmd (branching: 1,2→3→4→5→6)."""

    @pytest.fixture
    def graph_data(self):
        wf = parse_workflow(FIXTURES_DIR / "joins" / "join_workflow.yxmd")
        g = build_graph(wf)
        return wf, g

    def test_topological_order(self, graph_data):
        wf, g = graph_data
        order = execution_order(g)
        # Tools 1 and 2 must come before 3
        assert order.index(1) < order.index(3)
        assert order.index(2) < order.index(3)
        # Linear chain: 3→4→5→6
        assert order.index(3) < order.index(4)
        assert order.index(4) < order.index(5)
        assert order.index(5) < order.index(6)

    def test_join_input_ordering(self, graph_data):
        """Verify Join tool receives [left_df, right_df] in correct order."""
        wf, _ = graph_data
        imap = build_input_map(wf)
        join_inputs = imap[3]
        assert len(join_inputs) == 2
        # Tool 1 connects to Left, Tool 2 connects to Right
        assert join_inputs[0] == "df_1"   # Left
        assert join_inputs[1] == "df_2"   # Right


class TestResolveOutputVariable:
    """Test anchor → variable name mapping."""

    def test_single_output(self):
        assert resolve_output_variable(5, "Output") == "df_5"

    def test_filter_true(self):
        assert resolve_output_variable(3, "True") == "df_3_true"

    def test_filter_false(self):
        assert resolve_output_variable(3, "False") == "df_3_false"

    def test_join_joined(self):
        assert resolve_output_variable(7, "Join") == "df_7_joined"

    def test_join_left(self):
        assert resolve_output_variable(7, "Left") == "df_7_left_only"

    def test_join_right(self):
        assert resolve_output_variable(7, "Right") == "df_7_right_only"

    def test_unique(self):
        assert resolve_output_variable(10, "Unique") == "df_10_unique"

    def test_duplicates(self):
        assert resolve_output_variable(10, "Duplicates") == "df_10_duplicates"
