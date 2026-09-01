"""Deterministic unit tests for Workflow Complexity Engine."""

from __future__ import annotations

from types import SimpleNamespace
import networkx as nx
import pytest

from awa.analysis.workflow_complexity import (
    calculate_workflow_complexity,
    COMPLEXITY_WEIGHTS,
    COMPLEXITY_LOW_MAX,
    COMPLEXITY_MEDIUM_MAX,
    TOOL_COMPLEXITY_WEIGHTS,
)
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.connection import Connection


def _build_mock_result(
    tools: list[tuple[int, str, dict | None]],
    connections: list[tuple[int, int]],
) -> CanonicalAnalysisResult:
    """Helper to assemble a CanonicalAnalysisResult with specific tools and connections."""
    tool_dict: dict[int, Tool] = {}
    graph = nx.DiGraph()

    for tid, ttype, parsed_cfg in tools:
        cfg = ToolConfiguration(raw_xml="", parsed=parsed_cfg or {})
        t = Tool(
            tool_id=tid,
            plugin=f"AlteryxBasePluginsGui.{ttype}.{ttype}",
            tool_type=ttype,
            name=f"Tool {tid}",
            position=Position(x=100 * tid, y=100),
            configuration=cfg,
        )
        tool_dict[tid] = t
        graph.add_node(tid)

    conn_objs: list[Connection] = []
    for origin, target in connections:
        conn_objs.append(Connection(
            origin_tool_id=origin,
            origin_anchor="Output",
            destination_tool_id=target,
            destination_anchor="Input",
        ))
        graph.add_edge(origin, target)

    wf = Workflow(
        metadata=WorkflowMetadata(name="Test Workflow", version="2023.1"),
        tools=tool_dict,
        connections=conn_objs,
    )
    metrics = WorkflowMetrics(
        total_nodes=len(tools),
        total_connections=len(connections),
        input_count=1,
        output_count=1,
    )

    return SimpleNamespace(
        analysis_id="test_wf_001",
        workflow=wf,
        graph=graph,
        metrics=metrics,
    )


class TestWorkflowComplexity:
    def test_empty_workflow_produces_zero_low(self):
        """Empty workflow must yield 0.0 score and LOW complexity."""
        res = _build_mock_result([], [])
        assessment = calculate_workflow_complexity(res)
        assert assessment.score == 0.0
        assert assessment.level == "LOW"
        assert "Empty workflow" in assessment.factors[0]

    def test_tiny_linear_workflow_is_low_complexity(self):
        """A simple linear 3-tool pipeline (Input -> Filter -> Output) must be LOW complexity."""
        tools = [
            (1, "DbFileInput", {"file_path": "data.csv"}),
            (2, "Filter", {"expression": "[Age] > 21"}),
            (3, "DbFileOutput", {"file_path": "out.csv"}),
        ]
        connections = [(1, 2), (2, 3)]
        res = _build_mock_result(tools, connections)

        assessment = calculate_workflow_complexity(res)
        assert assessment.score <= COMPLEXITY_LOW_MAX
        assert assessment.level == "LOW"
        assert assessment.breakdown["topology"] <= 20.0  # Linear graph

    def test_medium_transformation_workflow_is_medium(self):
        """A workflow with multiple formulas, summaries, and joins scores MEDIUM."""
        tools = [
            (1, "DbFileInput", {"file_path": "sales.csv"}),
            (2, "DbFileInput", {"file_path": "lookup.csv"}),
            (3, "DbFileInput", {"file_path": "targets.csv"}),
            (4, "Formula", {"formula_fields": [{"expression": "[Amount] * 1.2"}]}),
            (5, "Join", {}),
            (6, "Join", {}),
            (7, "Union", {}),
            (8, "Summarize", {}),
            (9, "Sort", {}),
            (10, "Select", {}),
            (11, "Filter", {"expression": "[Amount] > 100 AND [Status] == 'ACTIVE'"}),
            (12, "Formula", {"formula_fields": [{"expression": "IF [Tax] > 0 THEN [Tax] ELSE 0 ENDIF"}]}),
            (13, "DbFileOutput", {"file_path": "out1.csv"}),
            (14, "DbFileOutput", {"file_path": "out2.csv"}),
        ]
        connections = [
            (1, 4), (4, 5), (2, 5), (5, 6), (3, 6),
            (6, 7), (7, 8), (8, 9), (9, 10), (10, 11),
            (11, 12), (12, 13), (11, 14)
        ]
        res = _build_mock_result(tools, connections)

        assessment = calculate_workflow_complexity(res)
        assert COMPLEXITY_LOW_MAX < assessment.score <= COMPLEXITY_MEDIUM_MAX
        assert assessment.level == "MEDIUM"
        assert any("join" in f for f in assessment.factors)

    def test_large_branched_workflow_is_high_complexity(self):
        """Large workflow with 35+ tools, multiple joins, branches, and merges must score HIGH."""
        tools = []
        connections = []
        # Create 38 tools with joins, crosstabs, and formulas
        for i in range(1, 39):
            if i in (5, 10, 15, 20):
                ttype = "Join"
            elif i in (8, 18, 28):
                ttype = "CrossTab"
            elif i in (12, 22, 32):
                ttype = "MultiRowFormula"
            elif i % 4 == 0:
                ttype = "Formula"
                cfg = {"formula_fields": [{"expression": "IF [A] > 10 THEN [B] ELSE [C] ENDIF"}]}
            else:
                ttype = "Select"
                cfg = None
            tools.append((i, ttype, cfg if i % 4 == 0 else None))
            if i > 1:
                connections.append((i - 1, i))
                if i % 3 == 0 and i + 2 <= 38:
                    connections.append((i - 1, i + 2))  # Branch points

        res = _build_mock_result(tools, connections)
        assessment = calculate_workflow_complexity(res)

        assert assessment.score >= 70.0
        assert assessment.level == "HIGH"
        assert any("tools" in f for f in assessment.factors)
        assert any("join" in f for f in assessment.factors)

    def test_python_and_macros_increase_runtime_complexity(self):
        """Workflows with Python or external Macros gain substantial runtime complexity points."""
        base_tools = [
            (1, "DbFileInput", {}),
            (2, "Select", {}),
            (3, "DbFileOutput", {}),
        ]
        base_conns = [(1, 2), (2, 3)]
        base_res = _build_mock_result(base_tools, base_conns)
        base_assessment = calculate_workflow_complexity(base_res)

        py_tools = [
            (1, "DbFileInput", {}),
            (2, "Python", {}),
            (3, "DbFileOutput", {}),
        ]
        py_res = _build_mock_result(py_tools, base_conns)
        py_assessment = calculate_workflow_complexity(py_res)

        assert py_assessment.score > base_assessment.score
        assert py_assessment.breakdown["runtime"] >= 40.0
        assert any("Python" in f for f in py_assessment.factors)

    def test_expression_complexity_conditional_detection(self):
        """Nested conditional expressions increase expression score."""
        simple_tools = [
            (1, "DbFileInput", {}),
            (2, "Formula", {"formula_fields": [{"expression": "[A] + [B]"}]}),
            (3, "DbFileOutput", {}),
        ]
        simple_res = _build_mock_result(simple_tools, [(1, 2), (2, 3)])
        simple_score = calculate_workflow_complexity(simple_res).breakdown["expression"]

        complex_tools = [
            (1, "DbFileInput", {}),
            (2, "Formula", {
                "formula_fields": [
                    {"expression": "IF [A] > 10 AND [B] == 'YES' THEN [C] ELSEIF [D] < 0 THEN [E] ELSE 0 ENDIF"},
                    {"expression": "IIF(DateTimeDiff(DateTimeToday(), [Date], 'days') > 30, 'Old', 'New')"},
                ]
            }),
            (3, "DbFileOutput", {}),
        ]
        complex_res = _build_mock_result(complex_tools, [(1, 2), (2, 3)])
        complex_score = calculate_workflow_complexity(complex_res).breakdown["expression"]

        assert complex_score > simple_score

    def test_score_remains_strictly_clamped_0_to_100(self):
        """Scores must strictly stay in [0.0, 100.0] even under extreme workflow size."""
        huge_tools = [(i, "Python", {}) for i in range(1, 100)]
        huge_conns = [(i, i + 1) for i in range(1, 99)] + [(i, i + 2) for i in range(1, 50, 2)]
        res = _build_mock_result(huge_tools, huge_conns)

        assessment = calculate_workflow_complexity(res)
        assert 0.0 <= assessment.score <= 100.0
        assert assessment.level == "HIGH"

    def test_deterministic_reproducibility(self):
        """Running calculation multiple times on identical input must yield identical results."""
        tools = [
            (1, "DbFileInput", {}),
            (2, "Join", {}),
            (3, "Formula", {"formula_fields": [{"expression": "[X] * 2"}]}),
            (4, "DbFileOutput", {}),
        ]
        res1 = _build_mock_result(tools, [(1, 2), (2, 3), (3, 4)])
        res2 = _build_mock_result(tools, [(1, 2), (2, 3), (3, 4)])

        a1 = calculate_workflow_complexity(res1)
        a2 = calculate_workflow_complexity(res2)

        assert a1.score == a2.score
        assert a1.level == a2.level
        assert a1.factors == a2.factors
