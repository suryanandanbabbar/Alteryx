"""Deterministic unit tests for Workflow Fingerprint extraction in ETL Rationalisation."""

from __future__ import annotations

import networkx as nx
import pytest
from types import SimpleNamespace

from awa.analysis.rationalisation_analyzer import (
    build_workflow_fingerprint,
    normalize_name,
    normalize_expression,
)
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.connection import Connection
from awa.model.field import Field
from awa.model.portfolio import PortfolioWorkflowSummary
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.workflow import Workflow, WorkflowMetadata


def _create_test_workflow(
    workflow_id: str,
    filename: str,
    sources: list[str],
    targets: list[str],
    inspection_sinks: list[str],
    tools_spec: list[tuple[int, str, str]],  # (id, type, raw_xml)
    connections_spec: list[tuple[int, int]],
    output_schema_fields: list[str] | None = None,
) -> tuple[PortfolioWorkflowSummary, CanonicalAnalysisResult]:
    """Helper to assemble a workflow and summary for fingerprinting."""
    tool_dict: dict[int, Tool] = {}
    g = nx.DiGraph()

    for tid, ttype, raw_xml in tools_spec:
        cfg = ToolConfiguration(raw_xml=raw_xml, parsed={})
        t = Tool(
            tool_id=tid,
            plugin=f"AlteryxBasePluginsGui.{ttype}.{ttype}",
            tool_type=ttype,
            name=f"{ttype}_{tid}",
            position=Position(x=100 * tid, y=100),
            configuration=cfg,
        )
        tool_dict[tid] = t
        g.add_node(tid)

    conn_objs: list[Connection] = []
    for origin, target in connections_spec:
        conn_objs.append(Connection(
            origin_tool_id=origin,
            origin_anchor="Output",
            destination_tool_id=target,
            destination_anchor="Input",
        ))
        g.add_edge(origin, target)

    wf = Workflow(
        metadata=WorkflowMetadata(name=filename, version="2023.1"),
        tools=tool_dict,
        connections=conn_objs,
    )
    metrics = WorkflowMetrics(
        total_nodes=len(tools_spec),
        total_connections=len(connections_spec),
        input_count=len(sources),
        output_count=len(targets),
    )
    dag = SimpleNamespace(graph=g)

    out_schema = None
    if output_schema_fields:
        out_schema = SimpleNamespace(fields=[Field(name=f, type="V_WString", size=100) for f in output_schema_fields])

    res = SimpleNamespace(
        analysis_id=workflow_id,
        workflow=wf,
        graph=g,
        metrics=metrics,
        output_schema=out_schema,
        lineage=None,
    )

    summary = PortfolioWorkflowSummary(
        workflow_id=workflow_id,
        filename=filename,
        relative_path=filename,
        status="SUCCESS",
        node_count=len(tools_spec),
        connection_count=len(connections_spec),
        sources=sources,
        targets=targets,
        inspection_sinks=inspection_sinks,
        complexity_level="MEDIUM",
        complexity_score=50.0,
        criticality_level="MEDIUM",
        criticality_score=50.0,
    )

    return summary, res


class TestRationalisationFingerprint:
    """Test deterministic fingerprint creation from canonical workflow IR."""

    def test_fingerprint_reproducibility(self):
        """Identical workflow input must yield identical fingerprint."""
        tools = [
            (1, "DbFileInput", "<File>Customer.xlsx</File>"),
            (2, "Filter", "<Expression>[Status] = 'Active'</Expression>"),
            (3, "DbFileOutput", "<File>Active_Customers.yxdb</File>"),
        ]
        conns = [(1, 2), (2, 3)]
        s1, res1 = _create_test_workflow("wf_1", "Customer_A.yxmd", ["Customer.xlsx"], ["Active_Customers.yxdb"], [], tools, conns)
        s2, res2 = _create_test_workflow("wf_1", "Customer_A.yxmd", ["Customer.xlsx"], ["Active_Customers.yxdb"], [], tools, conns)

        fp1 = build_workflow_fingerprint(s1, res1)
        fp2 = build_workflow_fingerprint(s2, res2)

        assert fp1.to_dict() == fp2.to_dict()
        assert fp1.sources == ["customer"]
        assert fp1.production_targets == ["active_customers"]

    def test_unknown_sources_and_targets_excluded(self):
        """*Unknown, blank, and invalid source/target placeholders must be stripped."""
        tools = [(1, "DbFileInput", ""), (2, "DbFileOutput", "")]
        conns = [(1, 2)]
        s, res = _create_test_workflow(
            "wf_unk", "Unknown_Test.yxmd",
            sources=["*Unknown", "", "Sales_Data.xlsx"],
            targets=["*Unknown", "Summary_Report.csv"],
            inspection_sinks=[],
            tools_spec=tools,
            connections_spec=conns,
        )
        fp = build_workflow_fingerprint(s, res)

        assert "*Unknown" not in fp.sources
        assert "*unknown" not in fp.sources
        assert "" not in fp.sources
        assert fp.sources == ["sales_data"]
        assert "*Unknown" not in fp.production_targets
        assert fp.production_targets == ["summary_report"]

    def test_inspection_sinks_strictly_segregated_from_targets(self):
        """Browse/BrowseV2 inspection sinks must not contaminate production targets."""
        tools = [
            (1, "DbFileInput", ""),
            (2, "BrowseV2", ""),
        ]
        conns = [(1, 2)]
        s, res = _create_test_workflow(
            "wf_browse", "Browse_Workflow.yxmd",
            sources=["Input.csv"],
            targets=[],  # No production targets!
            inspection_sinks=["BrowseV2 (Tool 2)"],
            tools_spec=tools,
            connections_spec=conns,
        )
        fp = build_workflow_fingerprint(s, res)

        assert len(fp.production_targets) == 0
        assert len(fp.inspection_sinks) == 1
        assert "browsev2" in fp.inspection_sinks[0]

    def test_output_schema_and_grain_capture(self):
        """Output schema column names and Summarize GroupBy grain fields must be captured."""
        summarize_xml = """<Configuration>
            <SummarizeFields>
                <SummarizeField field="CustomerID" action="GroupBy" rename="CustomerID" />
                <SummarizeField field="Region" action="GroupBy" rename="Region" />
                <SummarizeField field="Amount" action="Sum" rename="TotalAmount" />
            </SummarizeFields>
        </Configuration>"""

        tools = [
            (1, "DbFileInput", ""),
            (2, "Summarize", summarize_xml),
            (3, "DbFileOutput", ""),
        ]
        conns = [(1, 2), (2, 3)]
        s, res = _create_test_workflow(
            "wf_grain", "Grain_Test.yxmd",
            sources=["Transactions.yxdb"],
            targets=["Customer_Regional_Summary.yxdb"],
            inspection_sinks=[],
            tools_spec=tools,
            connections_spec=conns,
            output_schema_fields=["CustomerID", "Region", "TotalAmount"],
        )
        fp = build_workflow_fingerprint(s, res)

        assert "customerid" in fp.output_grain
        assert "region" in fp.output_grain
        assert fp.output_schemas["customer_regional_summary"] == ["CustomerID", "Region", "TotalAmount"]

    def test_transformation_signatures_captured(self):
        """Filters, joins, aggregations, Python, and macros must produce normalized signatures."""
        tools = [
            (1, "DbFileInput", ""),
            (2, "Filter", "<Expression>[Sales] > 1000 AND [Region] = 'EMEA'</Expression>"),
            (3, "Join", ""),
            (4, "Python", ""),
            (5, "DbFileOutput", ""),
        ]
        conns = [(1, 2), (2, 3), (3, 4), (4, 5)]
        s, res = _create_test_workflow("wf_sig", "Sig_Test.yxmd", ["Source.xlsx"], ["Target.yxdb"], [], tools, conns)
        fp = build_workflow_fingerprint(s, res)

        assert fp.has_python is True
        assert any("Filter:" in sig for sig in fp.transformation_signatures)
        assert any("Python" in sig for sig in fp.transformation_signatures)
        assert any("Join" in sig for sig in fp.transformation_signatures)

    def test_dag_topology_metrics_captured(self):
        """DAG node count, depth, branch and merge points must be correctly derived."""
        # 1 -> 2 -> 4
        # 1 -> 3 -> 4
        tools = [
            (1, "DbFileInput", ""),
            (2, "Formula", ""),
            (3, "Select", ""),
            (4, "Join", ""),
        ]
        conns = [(1, 2), (1, 3), (2, 4), (3, 4)]
        s, res = _create_test_workflow("wf_dag", "DAG_Test.yxmd", ["In.csv"], ["Out.csv"], [], tools, conns)
        fp = build_workflow_fingerprint(s, res)

        assert fp.node_count == 4
        assert fp.edge_count == 4
        assert fp.branch_points == 1  # node 1 has out_degree 2
        assert fp.merge_points == 1   # node 4 has in_degree 2
        assert fp.dag_depth == 2      # longest path length is 2
