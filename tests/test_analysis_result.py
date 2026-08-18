"""Tests for the Canonical Analysis Result and related models."""

import networkx as nx
import pytest

from backend.src.awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from backend.src.awa.model.source_info import SourceInfo, PackageMetadata
from backend.src.awa.model.visual_category import get_visual_category, get_tool_colors, get_category_colors, CATEGORY_COLORS
from backend.src.awa.model.python_trace import PythonTraceEntry, PythonTraceMap, ToolExplanation
from backend.src.awa.model.dag_layout import DagNodeLayout, DagEdgeLayout, DagLayout
from backend.src.awa.model.doc_model import NodeDocEntry, ExecutionStepDocEntry, DocumentModel
from backend.src.awa.model.workflow import Workflow, WorkflowMetadata
from backend.src.awa.model.tool import Tool, ToolConfiguration
from backend.src.awa.model.diagnostic import Diagnostic, DiagnosticLevel, SupportLevel
from backend.src.awa.model.translation import TranslationResult


def test_visual_categories_and_colors():
    assert get_visual_category("DbFileInput") == "input"
    assert get_visual_category("InputData") == "input"
    assert get_visual_category("DbFileOutput") == "output"
    assert get_visual_category("Filter") == "filter"
    assert get_visual_category("DateTime") == "datetime"
    assert get_visual_category("Summarize") == "summarize"
    assert get_visual_category("Join") == "join"
    assert get_visual_category("NonExistentTool") == "transform"

    input_colors = get_tool_colors("DbFileInput")
    assert "fill" in input_colors
    assert "stroke" in input_colors
    assert "badge" in input_colors
    assert "text" in input_colors
    assert input_colors["badge"] == CATEGORY_COLORS["input"]["badge"]


def test_source_info_serialization():
    si = SourceInfo(
        source_format="yxwz",
        original_filename="sample_package.yxwz",
        package_metadata=PackageMetadata(
            primary_workflow="workflow.yxmd",
            contained_files=["workflow.yxmd", "data.csv"],
            total_size_bytes=1024,
        ),
    )
    d = si.to_dict()
    assert d["source_format"] == "yxwz"
    assert d["original_filename"] == "sample_package.yxwz"
    assert d["package_metadata"]["primary_workflow"] == "workflow.yxmd"
    assert len(d["package_metadata"]["contained_files"]) == 2


def test_python_trace_and_explanations():
    entry = PythonTraceEntry(
        tool_id=1,
        tool_type="Filter",
        tool_name="Filter Active",
        start_line=10,
        end_line=15,
        description="Filter rows where status is active",
        pandas_op="df[df['status'] == 'active']",
        reason="Direct pandas boolean indexing",
        libraries=["pandas"],
    )
    tmap = PythonTraceMap(entries=[entry], total_lines=20)
    assert tmap.get_entry(1) == entry
    assert tmap.get_entry(999) is None

    exp = ToolExplanation(
        what_alteryx_does="Filter records matching condition",
        what_pandas_does="Boolean mask indexing",
        why_selected="Idiomatic pandas filter",
        libraries=["pandas"],
    )
    assert exp.to_dict()["what_alteryx_does"] == "Filter records matching condition"


def test_dag_layout_model():
    node = DagNodeLayout(
        tool_id=1,
        x=100.0,
        y=50.0,
        width=160.0,
        height=60.0,
        label="Input 1",
        tool_type="DbFileInput",
        execution_index=0,
        visual_category="input",
    )
    edge = DagEdgeLayout(
        source_id=1,
        target_id=2,
        source_anchor="Output",
        target_anchor="Input",
        path_points=[(260.0, 80.0), (320.0, 80.0)],
    )
    layout = DagLayout(nodes=[node], edges=[edge], width=500.0, height=300.0, title="Test DAG")
    assert layout.get_node(1) == node
    assert layout.get_node(2) is None
    d = layout.to_dict()
    assert len(d["nodes"]) == 1
    assert len(d["edges"]) == 1
    assert d["title"] == "Test DAG"


def test_canonical_analysis_result():
    wf_meta = WorkflowMetadata(name="Test Workflow", version="2025.1")
    tool = Tool(
        tool_id=1,
        plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
        tool_type="DbFileInput",
        name="Input",
        position=None,
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "data.csv"}),
    )
    wf = Workflow(metadata=wf_meta, tools={1: tool})
    g = nx.DiGraph()
    g.add_node(1, tool=tool)

    tr = TranslationResult(
        tool_id=1,
        tool_type="DbFileInput",
        support_level=SupportLevel.SUPPORTED,
        python_code="df_1 = pd.read_csv('data.csv')",
        imports={"import pandas as pd"},
        input_variables=[],
        output_map={"Output": "df_1"},
    )

    metrics = WorkflowMetrics(
        total_nodes=1,
        total_connections=0,
        input_count=1,
        output_count=0,
        input_node_ids=[1],
        output_node_ids=[],
        support_summary={"supported": 1},
    )

    layout = DagLayout(nodes=[], edges=[], width=200, height=100, title="Test")
    tmap = PythonTraceMap(entries=[], total_lines=5)

    res = CanonicalAnalysisResult(
        analysis_id="test-uuid",
        source=SourceInfo(source_format="yxmd", original_filename="test.yxmd"),
        workflow=wf,
        graph=g,
        execution_order=[1],
        translations={1: tr},
        consumed_anchors={1: {"Output"}},
        lineage_paths=[],
        metrics=metrics,
        dag_layout=layout,
        python_trace=tmap,
        tool_explanations={},
        required_libraries=["pandas"],
        diagnostics=[],
    )

    d = res.to_dict()
    assert d["analysis_id"] == "test-uuid"
    assert d["source"]["source_format"] == "yxmd"
    assert d["metrics"]["total_nodes"] == 1
    assert d["required_libraries"] == ["pandas"]
