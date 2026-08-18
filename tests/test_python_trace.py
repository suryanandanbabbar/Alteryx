"""Tests for Python line-level traceability and library disclosure."""

from awa.parser.xml_parser import parse_workflow
from awa.graph.builder import build_graph, execution_order, consumed_anchors, build_input_map
from awa.translators.registry import get_translator
import awa.translators  # register
from awa.generators.python_generator import generate_python_code
from awa.analysis.workflow_analyzer import analyze_canonical


def test_python_trace_line_accuracy():
    canonical = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    trace_map = canonical.python_trace

    assert len(trace_map.entries) == 3
    code, _, _ = generate_python_code(
        canonical.workflow,
        canonical.execution_order,
        canonical.translations,
        canonical.consumed_anchors,
    )
    code_lines = code.splitlines()
    assert trace_map.total_lines == len(code_lines)

    for entry in trace_map.entries:
        assert 1 <= entry.start_line <= entry.end_line <= trace_map.total_lines
        # The start line should contain the tool header comment
        start_snippet = code_lines[entry.start_line - 1]
        assert f"Tool #{entry.tool_id}" in start_snippet


def test_python_library_disclosure():
    canonical = analyze_canonical("fixtures/joins/join_workflow.yxmd")
    # Only generated-code dependencies (e.g. pandas) should be disclosed
    assert "pandas" in canonical.required_libraries
    # AWA analyzer dependencies must NOT be in the generated workflow requirements
    assert "networkx" not in canonical.required_libraries
    assert "lark" not in canonical.required_libraries
    assert "fastapi" not in canonical.required_libraries
    assert "docx" not in canonical.required_libraries


def test_tool_explanations_deterministic():
    canonical = analyze_canonical("fixtures/joins/join_workflow.yxmd")
    assert len(canonical.tool_explanations) == 6

    for tid, exp in canonical.tool_explanations.items():
        assert len(exp.what_alteryx_does) > 0
        assert len(exp.what_pandas_does) > 0
        assert len(exp.why_selected) > 0
        assert "pandas" in exp.libraries
