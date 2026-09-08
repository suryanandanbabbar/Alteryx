"""Deterministic unit tests for ETL Rationalisation 3-way partition filters:
Retire, Consolidate, Keep.

Validates:
1. Review becomes Retire (recommendation mapped to RETIRE, original provenance preserved)
2. Valid Consolidate remains Consolidate (source overlap > 60% + MERGE)
3. Non-candidate workflows become Keep
4. Shared Logic workflows become Keep at workflow level
5. Complete Partition (Retire U Consolidate U Keep = N, disjoint sets, counts sum to N)
6. Refresh stability (persisted & reloaded results produce identical classification)
7. Processing-order stability (input order permutations produce identical classifications)
"""

from __future__ import annotations

import random
from types import SimpleNamespace
from typing import Any
import networkx as nx
import pytest

from awa.analysis.rationalisation_analyzer import (
    build_rationalisation_analysis,
    compare_workflows,
    detect_candidate_from_comparison,
    evaluate_consolidation_rules,
    ConsolidationRules,
    RationalisationThresholds,
)
from awa.model.analysis_result import WorkflowMetrics
from awa.model.connection import Connection
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.portfolio import (
    PortfolioAggregateMetrics,
    PortfolioAnalysis,
    PortfolioWorkflowSummary,
    RationalisationAnalysis,
    WorkflowFingerprint,
)


def _make_test_workflow(
    workflow_id: str,
    filename: str,
    sources: list[str],
    targets: list[str],
    tools_spec: list[tuple[int, str, dict, str]],
    inspection_sinks: list[str] | None = None,
    complexity_level: str = "MEDIUM",
    complexity_score: float = 50.0,
    criticality_level: str = "MEDIUM",
    criticality_score: float = 50.0,
    frequency: str = "Daily",
) -> tuple[PortfolioWorkflowSummary, Any]:
    """Helper to assemble a workflow and summary for testing rationalisation."""
    tool_dict: dict[int, Tool] = {}
    g = nx.DiGraph()

    for tid, ttype, parsed, raw_xml in tools_spec:
        cfg = ToolConfiguration(raw_xml=raw_xml, parsed=parsed)
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

    conns = []
    tids = [spec[0] for spec in tools_spec]
    for i in range(len(tids) - 1):
        conns.append(Connection(
            origin_tool_id=tids[i],
            origin_anchor="Output",
            destination_tool_id=tids[i + 1],
            destination_anchor="Input",
        ))
        g.add_edge(tids[i], tids[i + 1])

    wf = Workflow(
        metadata=WorkflowMetadata(name=filename, version="2023.1"),
        tools=tool_dict,
        connections=conns,
    )
    metrics = WorkflowMetrics(
        total_nodes=len(tools_spec),
        total_connections=len(conns),
        input_count=len(sources),
        output_count=len(targets),
    )

    res = SimpleNamespace(
        analysis_id=workflow_id,
        workflow=wf,
        graph=g,
        metrics=metrics,
        output_schema=None,
        lineage=None,
    )

    summary = PortfolioWorkflowSummary(
        workflow_id=workflow_id,
        filename=filename,
        relative_path=filename,
        status="SUCCESS",
        node_count=len(tools_spec),
        connection_count=len(conns),
        sources=sources,
        targets=targets,
        inspection_sinks=inspection_sinks or [],
        complexity_level=complexity_level,
        complexity_score=complexity_score,
        criticality_level=criticality_level,
        criticality_score=criticality_score,
        frequency=frequency,
        business_purpose=f"Purpose of {filename}",
    )

    return summary, res


def _make_portfolio(items: list[tuple[PortfolioWorkflowSummary, Any]], port_id: str = "test_port") -> tuple[PortfolioAnalysis, dict[str, Any]]:
    summaries = [it[0] for it in items]
    results = {it[0].workflow_id: it[1] for it in items}
    portfolio = PortfolioAnalysis(
        portfolio_id=port_id,
        portfolio_name=f"Portfolio {port_id}",
        workflow_count=len(summaries),
        workflows=summaries,
        metrics=PortfolioAggregateMetrics(total_workflows=len(summaries)),
        shared_sources=[],
        shared_targets=[],
        relationships=[],
        rationalisation_candidates=[],
    )
    return portfolio, results


class TestRationalisationFilters:
    """Comprehensive test suite for Retire / Consolidate / Keep classification model."""

    def test_review_becomes_retire(self):
        """Test 1: Every workflow / candidate previously under Review is classified as RETIRE."""
        # A workflow with ONLY inspection sinks and NO production targets
        w_sink = _make_test_workflow(
            "wf_sink",
            "Debug_Inspect.yxmd",
            sources=["raw_data.csv"],
            targets=[],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "raw_data.csv"}, '<Configuration><File>raw_data.csv</File></Configuration>'),
                (2, "BrowseV2", {"temp_file": "temp_browse.yxdb"}, '<Configuration><TempFile>temp_browse.yxdb</TempFile></Configuration>'),
            ],
            inspection_sinks=["temp_browse.yxdb"],
        )

        w_prod = _make_test_workflow(
            "wf_prod",
            "Production_Report.yxmd",
            sources=["sales.csv"],
            targets=["report.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "sales.csv"}, '<Configuration><File>sales.csv</File></Configuration>'),
                (2, "DbFileOutput", {"file_path": "report.yxdb"}, '<Configuration><File>report.yxdb</File></Configuration>'),
            ],
        )

        portfolio, results = _make_portfolio([w_sink, w_prod], "port_retire")
        analysis = build_rationalisation_analysis(portfolio, results, use_llm=False)

        # Inspect candidate generated for wf_sink
        sink_cands = [c for c in analysis.candidates if "wf_sink" in c.workflow_ids]
        assert len(sink_cands) >= 1
        for cand in sink_cands:
            assert cand.recommendation_type in ("RETIRE", "RETIRE_CANDIDATE")
            assert cand.original_recommendation_type in ("REVIEW", "RETIRE")

        # Workflow-level classification
        assert analysis.workflow_classifications["wf_sink"] == "RETIRE"
        assert w_sink[0].rationalisation_status == "RETIRE"
        assert analysis.workflow_counts["RETIRE"] == 1

    def test_valid_consolidate_remains_consolidate(self):
        """Test 2: Valid Consolidate candidates (source overlap > 60% + MERGE) remain CONSOLIDATE."""
        # Workflow A is a data subset of Workflow B with identical source and target
        w_a = _make_test_workflow(
            "wf_a",
            "Workflow_01.yxmd",
            sources=["claims.csv"],
            targets=["claims_summary.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "claims.csv"}, '<Configuration><File>claims.csv</File><Fields><Field name="claim_id"/><Field name="amount"/></Fields></Configuration>'),
                (2, "Filter", {"expression": "amount > 0"}, '<Configuration><Expression>amount &gt; 0</Expression></Configuration>'),
                (3, "DbFileOutput", {"file_path": "claims_summary.yxdb"}, '<Configuration><File>claims_summary.yxdb</File></Configuration>'),
            ],
            complexity_level="LOW",
            complexity_score=20.0,
        )

        w_b = _make_test_workflow(
            "wf_b",
            "WF03.yxmd",
            sources=["claims.csv"],
            targets=["claims_summary.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "claims.csv"}, '<Configuration><File>claims.csv</File><Fields><Field name="claim_id"/><Field name="amount"/><Field name="date"/></Fields></Configuration>'),
                (2, "Filter", {"expression": "amount > 0"}, '<Configuration><Expression>amount &gt; 0</Expression></Configuration>'),
                (3, "Formula", {"formula_fields": [{"field_name": "extra", "expression": "1"}]}, '<Configuration><FormulaFields><FormulaField field="extra" expression="1"/></FormulaFields></Configuration>'),
                (4, "DbFileOutput", {"file_path": "claims_summary.yxdb"}, '<Configuration><File>claims_summary.yxdb</File></Configuration>'),
            ],
        )

        portfolio, results = _make_portfolio([w_a, w_b], "port_cons")
        analysis = build_rationalisation_analysis(portfolio, results, use_llm=False)

        cons_cands = [c for c in analysis.candidates if c.recommendation_type == "CONSOLIDATE"]
        assert len(cons_cands) >= 1
        cand = cons_cands[0]
        assert cand.consolidation_decision is not None
        assert cand.consolidation_decision.recommendation == "MERGE"
        assert cand.deterministic_metrics.source_overlap > 0.60

        # Absorbed workflow is marked CONSOLIDATE
        assert analysis.workflow_classifications["wf_a"] == "CONSOLIDATE"

    def test_non_candidate_workflows_become_keep(self):
        """Test 3: Workflows with no rationalisation opportunities become KEEP."""
        w_1 = _make_test_workflow(
            "wf_1",
            "Finance_GL.yxmd",
            sources=["gl_entries.csv"],
            targets=["gl_monthly.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "gl_entries.csv"}, '<Configuration><File>gl_entries.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "bal", "expression": "dr-cr"}]}, '<Configuration><FormulaFields><FormulaField field="bal" expression="dr-cr"/></FormulaFields></Configuration>'),
                (3, "DbFileOutput", {"file_path": "gl_monthly.yxdb"}, '<Configuration><File>gl_monthly.yxdb</File></Configuration>'),
            ],
        )

        w_2 = _make_test_workflow(
            "wf_2",
            "HR_Payroll.yxmd",
            sources=["employees.csv"],
            targets=["payroll_summary.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "employees.csv"}, '<Configuration><File>employees.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "net", "expression": "gross-tax"}]}, '<Configuration><FormulaFields><FormulaField field="net" expression="gross-tax"/></FormulaFields></Configuration>'),
                (3, "DbFileOutput", {"file_path": "payroll_summary.yxdb"}, '<Configuration><File>payroll_summary.yxdb</File></Configuration>'),
            ],
        )

        portfolio, results = _make_portfolio([w_1, w_2], "port_keep")
        analysis = build_rationalisation_analysis(portfolio, results, use_llm=False)

        assert analysis.workflow_classifications["wf_1"] == "KEEP"
        assert analysis.workflow_classifications["wf_2"] == "KEEP"
        assert w_1[0].rationalisation_status == "KEEP"
        assert w_2[0].rationalisation_status == "KEEP"
        assert analysis.workflow_counts["KEEP"] == 2
        assert analysis.workflow_counts["CONSOLIDATE"] == 0
        assert analysis.workflow_counts["RETIRE"] == 0

    def test_shared_logic_workflows_become_keep_at_workflow_level(self):
        """Test 4: Workflows having shared logic but no data consolidation action become KEEP."""
        # Two workflows share formula structure but have disjoint sources and targets
        w_1 = _make_test_workflow(
            "wf_1",
            "Store_A.yxmd",
            sources=["store_a_pos.csv"],
            targets=["store_a_kpi.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "store_a_pos.csv"}, '<Configuration><File>store_a_pos.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "calc_tax", "expression": "revenue*0.2"}]}, '<Configuration><FormulaFields><FormulaField field="calc_tax" expression="revenue*0.2"/></FormulaFields></Configuration>'),
                (3, "Filter", {"expression": "region='US'"}, '<Configuration><Expression>region=&apos;US&apos;</Expression></Configuration>'),
                (4, "DbFileOutput", {"file_path": "store_a_kpi.yxdb"}, '<Configuration><File>store_a_kpi.yxdb</File></Configuration>'),
            ],
        )

        w_2 = _make_test_workflow(
            "wf_2",
            "Store_B.yxmd",
            sources=["store_b_pos.csv"],
            targets=["store_b_kpi.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "store_b_pos.csv"}, '<Configuration><File>store_b_pos.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "calc_tax", "expression": "revenue*0.2"}]}, '<Configuration><FormulaFields><FormulaField field="calc_tax" expression="revenue*0.2"/></FormulaFields></Configuration>'),
                (3, "Filter", {"expression": "region='US'"}, '<Configuration><Expression>region=&apos;US&apos;</Expression></Configuration>'),
                (4, "DbFileOutput", {"file_path": "store_b_kpi.yxdb"}, '<Configuration><File>store_b_kpi.yxdb</File></Configuration>'),
            ],
        )

        portfolio, results = _make_portfolio([w_1, w_2], "port_shared_logic")
        analysis = build_rationalisation_analysis(portfolio, results, use_llm=False)

        # Candidate can be emitted as SHARED_LOGIC similarity
        # But workflow classifications must be KEEP
        assert analysis.workflow_classifications["wf_1"] == "KEEP"
        assert analysis.workflow_classifications["wf_2"] == "KEEP"
        assert analysis.workflow_counts["KEEP"] == 2
        assert analysis.workflow_counts["CONSOLIDATE"] == 0
        assert analysis.workflow_counts["RETIRE"] == 0

    def test_complete_partition(self):
        """Test 5: Complete Partition - Retire U Consolidate U Keep = N, disjoint sets, sums to N."""
        # 1 Retire candidate (inspection sink)
        w_ret = _make_test_workflow(
            "wf_ret", "RetireMe.yxmd", ["raw.csv"], [],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "raw.csv"}, '<Configuration><File>raw.csv</File></Configuration>'),
                (2, "BrowseV2", {"temp_file": "browse.yxdb"}, '<Configuration><TempFile>browse.yxdb</TempFile></Configuration>'),
            ],
            inspection_sinks=["browse.yxdb"],
        )

        # 1 Consolidate pair (wf_sub absorbs into wf_super)
        w_sub = _make_test_workflow(
            "wf_sub", "Subset.yxmd", ["data.csv"], ["out.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "data.csv"}, '<Configuration><File>data.csv</File><Fields><Field name="id"/><Field name="val"/></Fields></Configuration>'),
                (2, "Filter", {"expression": "val>0"}, '<Configuration><Expression>val&gt;0</Expression></Configuration>'),
                (3, "DbFileOutput", {"file_path": "out.yxdb"}, '<Configuration><File>out.yxdb</File></Configuration>'),
            ],
            complexity_level="LOW",
            complexity_score=20.0,
        )

        w_super = _make_test_workflow(
            "wf_super", "Superset.yxmd", ["data.csv"], ["out.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "data.csv"}, '<Configuration><File>data.csv</File><Fields><Field name="id"/><Field name="val"/><Field name="extra"/></Fields></Configuration>'),
                (2, "Filter", {"expression": "val>0"}, '<Configuration><Expression>val&gt;0</Expression></Configuration>'),
                (3, "Formula", {"formula_fields": [{"field_name": "extra", "expression": "1"}]}, '<Configuration><FormulaFields><FormulaField field="extra" expression="1"/></FormulaFields></Configuration>'),
                (4, "DbFileOutput", {"file_path": "out.yxdb"}, '<Configuration><File>out.yxdb</File></Configuration>'),
            ],
        )

        # 2 Independent workflows -> KEEP
        w_k1 = _make_test_workflow(
            "wf_k1", "Keep1.yxmd", ["k1_in.csv"], ["k1_out.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "k1_in.csv"}, '<Configuration><File>k1_in.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "k1", "expression": "1"}]}, '<Configuration><FormulaFields><FormulaField field="k1" expression="1"/></FormulaFields></Configuration>'),
                (3, "DbFileOutput", {"file_path": "k1_out.yxdb"}, '<Configuration><File>k1_out.yxdb</File></Configuration>'),
            ],
        )

        w_k2 = _make_test_workflow(
            "wf_k2", "Keep2.yxmd", ["k2_in.csv"], ["k2_out.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "k2_in.csv"}, '<Configuration><File>k2_in.csv</File></Configuration>'),
                (2, "Formula", {"formula_fields": [{"field_name": "k2", "expression": "2"}]}, '<Configuration><FormulaFields><FormulaField field="k2" expression="2"/></FormulaFields></Configuration>'),
                (3, "DbFileOutput", {"file_path": "k2_out.yxdb"}, '<Configuration><File>k2_out.yxdb</File></Configuration>'),
            ],
        )

        all_items = [w_ret, w_sub, w_super, w_k1, w_k2]
        n_total = len(all_items)

        portfolio, results = _make_portfolio(all_items, "port_partition")
        analysis = build_rationalisation_analysis(portfolio, results, use_llm=False)

        # 1. Total count matches
        assert analysis.analysed_workflow_count == n_total
        assert len(analysis.workflow_classifications) == n_total

        # 2. Partition sets are disjoint and cover all workflows
        retire_set = {wid for wid, cat in analysis.workflow_classifications.items() if cat == "RETIRE"}
        consolidate_set = {wid for wid, cat in analysis.workflow_classifications.items() if cat == "CONSOLIDATE"}
        keep_set = {wid for wid, cat in analysis.workflow_classifications.items() if cat == "KEEP"}

        assert retire_set.isdisjoint(consolidate_set)
        assert retire_set.isdisjoint(keep_set)
        assert consolidate_set.isdisjoint(keep_set)

        all_union = retire_set | consolidate_set | keep_set
        assert all_union == {it[0].workflow_id for it in all_items}

        # 3. Counts sum to N
        retire_count = analysis.workflow_counts["RETIRE"]
        cons_count = analysis.workflow_counts["CONSOLIDATE"]
        keep_count = analysis.workflow_counts["KEEP"]

        assert retire_count == len(retire_set)
        assert cons_count == len(consolidate_set)
        assert keep_count == len(keep_set)
        assert retire_count + cons_count + keep_count == n_total

    def test_refresh_stability(self):
        """Test 6: Refresh stability - recomputing produces identical classifications."""
        w_1 = _make_test_workflow(
            "wf_1", "W1.yxmd", ["raw.csv"], [],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "raw.csv"}, '<Configuration><File>raw.csv</File></Configuration>'),
                (2, "BrowseV2", {"temp_file": "browse.yxdb"}, '<Configuration><TempFile>browse.yxdb</TempFile></Configuration>'),
            ],
            inspection_sinks=["browse.yxdb"],
        )

        w_2 = _make_test_workflow(
            "wf_2", "W2.yxmd", ["in2.csv"], ["out2.yxdb"],
            tools_spec=[
                (1, "DbFileInput", {"file_path": "in2.csv"}, '<Configuration><File>in2.csv</File></Configuration>'),
                (2, "DbFileOutput", {"file_path": "out2.yxdb"}, '<Configuration><File>out2.yxdb</File></Configuration>'),
            ],
        )

        portfolio, results = _make_portfolio([w_1, w_2], "port_refresh")

        analysis_run1 = build_rationalisation_analysis(portfolio, results, use_llm=False)
        dict_run1 = analysis_run1.to_dict()

        # Re-run
        analysis_run2 = build_rationalisation_analysis(portfolio, results, use_llm=False)
        dict_run2 = analysis_run2.to_dict()

        assert dict_run1["workflow_classifications"] == dict_run2["workflow_classifications"]
        assert dict_run1["workflow_counts"] == dict_run2["workflow_counts"]
        assert dict_run1["recommendation_counts"] == dict_run2["recommendation_counts"]

    def test_processing_order_stability(self):
        """Test 7: Processing-order stability - permutations of input workflows produce identical buckets."""
        all_items = [
            _make_test_workflow(
                f"wf_{i}", f"W{i}.yxmd", [f"in_{i}.csv"], [f"out_{i}.yxdb"],
                tools_spec=[
                    (1, "DbFileInput", {"file_path": f"in_{i}.csv"}, f'<Configuration><File>in_{i}.csv</File></Configuration>'),
                    (2, "Formula", {"formula_fields": [{"field_name": f"f{i}", "expression": str(i)}]}, f'<Configuration><FormulaFields><FormulaField field="f{i}" expression="{i}"/></FormulaFields></Configuration>'),
                    (3, "DbFileOutput", {"file_path": f"out_{i}.yxdb"}, f'<Configuration><File>out_{i}.yxdb</File></Configuration>'),
                ],
            )
            for i in range(6)
        ]

        # Order A
        portfolio_a, results_a = _make_portfolio(all_items, "port_order_a")
        analysis_a = build_rationalisation_analysis(portfolio_a, results_a, use_llm=False)

        # Order B (reversed)
        items_reversed = list(reversed(all_items))
        portfolio_b, results_b = _make_portfolio(items_reversed, "port_order_b")
        analysis_b = build_rationalisation_analysis(portfolio_b, results_b, use_llm=False)

        # Order C (shuffled)
        rng = random.Random(42)
        items_shuffled = list(all_items)
        rng.shuffle(items_shuffled)
        portfolio_c, results_c = _make_portfolio(items_shuffled, "port_order_c")
        analysis_c = build_rationalisation_analysis(portfolio_c, results_c, use_llm=False)

        assert analysis_a.workflow_classifications == analysis_b.workflow_classifications == analysis_c.workflow_classifications
        assert analysis_a.workflow_counts == analysis_b.workflow_counts == analysis_c.workflow_counts
