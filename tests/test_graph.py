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


class TestExecutionOrderAndOutputClassification:
    """Validate topological execution ordering, cycle detection, and terminal/business outputs."""

    def test_deterministic_kahn_topological_sort_repeatability(self):
        """Topological execution order must be 100% deterministic across repeated runs."""
        wf = parse_workflow("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        g = build_graph(wf)

        orders = [execution_order(g) for _ in range(10)]
        for o in orders[1:]:
            assert o == orders[0], "Topological order is not deterministic across runs!"

    def test_all_edges_dependency_ordering(self):
        """Every edge A -> B must satisfy position(A) < position(B) in execution_order."""
        wf = parse_workflow("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        g = build_graph(wf)
        order = execution_order(g)
        pos_map = {node: idx for idx, node in enumerate(order)}

        for u, v in g.edges():
            assert pos_map[u] < pos_map[v], f"Dependency violation: {u} (pos {pos_map[u]}) is not before {v} (pos {pos_map[v]})"

        # Explicitly verify required examples: 102 -> 104, 2 -> 111, 101 -> 111
        assert pos_map[102] < pos_map[104]
        assert pos_map[2] < pos_map[111]
        assert pos_map[101] < pos_map[111]

    def test_cyclic_workflow_error_detection(self):
        """Cycle in workflow graph raises CyclicWorkflowError."""
        import networkx as nx
        from awa.graph.builder import CyclicWorkflowError

        cyclic_g = nx.DiGraph()
        cyclic_g.add_edge(1, 2)
        cyclic_g.add_edge(2, 3)
        cyclic_g.add_edge(3, 1)

        with pytest.raises(CyclicWorkflowError):
            execution_order(cyclic_g)

    def test_terminal_vs_business_outputs_separation(self):
        """Terminal nodes (7) and Business Outputs (5) are explicitly separated on Demo Claims."""
        from awa.analysis.workflow_analyzer import analyze_canonical

        canonical = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        metrics = canonical.metrics

        # 1. Total counts
        assert metrics.terminal_node_count == 7
        assert metrics.business_output_count == 5
        assert metrics.output_count == 7

        # 2. Business output node IDs
        assert metrics.business_output_node_ids == [17, 18, 132, 142, 152]

        # 3. BrowseV2 nodes #7 and #14 are in terminal_node_ids but excluded from business outputs
        assert 7 in metrics.terminal_node_ids
        assert 14 in metrics.terminal_node_ids
        assert 7 not in metrics.business_output_node_ids
        assert 14 not in metrics.business_output_node_ids
