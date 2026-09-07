"""
Test suite for Deterministic Directional Data-Superset Merge Detection in ETL Rationalisation.
"""

import pytest
from pathlib import Path

from awa.model.portfolio import (
    PortfolioWorkflowSummary,
    PortfolioAnalysis,
    WorkflowFingerprint,
    ColumnEvidence,
    DataSubsumptionEvidence,
)
from awa.parser.xml_parser import parse_workflow
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.analysis.rationalisation_analyzer import (
    build_workflow_fingerprint,
    compare_workflows,
    evaluate_directional_data_subsumption,
    evaluate_consolidation_rules,
    detect_candidate_from_comparison,
    build_rationalisation_analysis,
    ConsolidationRules,
)


@pytest.fixture
def bbcfood_results():
    """Parse and analyze BBCFood v2 and BBCFoodAggr workflows from test fixtures / uploads."""
    data_dir = Path("/Users/surya/Documents/Projects/Alteryx")
    file_v2 = None
    file_aggr = None

    for p in data_dir.glob("**/*.yxmd"):
        if p.name == "BBCFood v2.yxmd":
            file_v2 = p
        elif p.name == "BBCFoodAggr.yxmd":
            file_aggr = p

    if not file_v2 or not file_aggr:
        pytest.skip("BBCFood test workflows not found in workspace.")

    res_v2 = analyze_canonical(file_v2)
    res_aggr = analyze_canonical(file_aggr)

    summary_v2 = PortfolioWorkflowSummary(
        workflow_id="wf_bbcfood_v2",
        filename="BBCFood v2.yxmd",
        relative_path="BBCFood v2.yxmd",
        status="SUCCESS",
        node_count=len(res_v2.workflow.tools),
        connection_count=len(res_v2.workflow.connections),
        sources=list(res_v2.sources.keys()) if hasattr(res_v2, "sources") else [],
        targets=list(res_v2.targets.keys()) if hasattr(res_v2, "targets") else [],
        inspection_sinks=[],
        tool_types=list({t.tool_type for t in res_v2.workflow.tools.values()}),
        business_purpose="BBC Food Recipe Scraper and Consolidated Store",
        sttm_mappings_count=0,
        complexity_level="MEDIUM",
        complexity_score=45.0,
        criticality_level="LOW",
        criticality_score=20.0,
        frequency="Daily",
    )

    summary_aggr = PortfolioWorkflowSummary(
        workflow_id="wf_bbcfood_aggr",
        filename="BBCFoodAggr.yxmd",
        relative_path="BBCFoodAggr.yxmd",
        status="SUCCESS",
        node_count=len(res_aggr.workflow.tools),
        connection_count=len(res_aggr.workflow.connections),
        sources=list(res_aggr.sources.keys()) if hasattr(res_aggr, "sources") else [],
        targets=[],
        inspection_sinks=["Browse (Tool #5)"],
        tool_types=list({t.tool_type for t in res_aggr.workflow.tools.values()}),
        business_purpose="BBC Food Aggregate View",
        sttm_mappings_count=0,
        complexity_level="LOW",
        complexity_score=15.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
    )

    return {
        "v2": (summary_v2, res_v2),
        "aggr": (summary_aggr, res_aggr),
    }


def test_directional_subsumption_bbcfood(bbcfood_results):
    """Verify that BBCFoodAggr is deterministically subsumed by BBCFood v2."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_aggr, fp_v2)

    # 1. Forward direction: BBCFoodAggr -> BBCFood v2
    subsumed_fwd, ev_fwd = evaluate_directional_data_subsumption(fp_aggr, fp_v2, comp)
    assert subsumed_fwd is True, "BBCFoodAggr should be subsumed by BBCFood v2"
    assert ev_fwd is not None
    assert ev_fwd.data_coverage_pct == 1.0
    assert ev_fwd.missing_fields_count == 0
    assert ev_fwd.processing_compatibility == "SUPPORTED"
    assert ev_fwd.output_compatibility in ("INSPECTION_SINK_ONLY", "COMPATIBLE")
    assert ev_fwd.has_unresolved_unique_functionality is False
    assert len(ev_fwd.shared_required_fields) > 0


def test_asymmetric_rejection_reverse_direction(bbcfood_results):
    """Verify that BBCFood v2 is NOT subsumed by BBCFoodAggr (strictly directional)."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_v2, fp_aggr)

    # 2. Reverse direction: BBCFood v2 -> BBCFoodAggr
    subsumed_rev, ev_rev = evaluate_directional_data_subsumption(fp_v2, fp_aggr, comp)
    assert subsumed_rev is False, "BBCFood v2 must NOT be subsumed by BBCFoodAggr"


def test_consolidation_rule_and_candidate_detection(bbcfood_results):
    """Verify that consolidation rule evaluation picks RULE_DATA_SUBSUMPTION and creates candidate."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_aggr, fp_v2)
    decision = evaluate_consolidation_rules(fp_aggr, fp_v2, comp)

    assert decision.recommendation == "MERGE"
    assert decision.matched_rule == ConsolidationRules.RULE_DATA_SUBSUMPTION
    assert decision.data_subsumption_evidence is not None

    cand = detect_candidate_from_comparison(comp, fp_aggr, fp_v2)
    assert cand is not None
    assert cand.recommendation_type == "CONSOLIDATE"
    assert cand.data_subsumption_evidence is not None
    assert "Directional Data Subsumption Confirmed" in cand.reasoning


def test_synthetic_missing_field_rejection():
    """Verify that a synthetic workflow with missing fields is rejected."""
    fp_source = WorkflowFingerprint(
        workflow_id="src_1",
        workflow_name="source_wf",
        sources=["input.csv"],
        source_types={"input.csv": "FILE"},
        source_fields={"input.csv": ["id", "amount", "missing_col"]},
        production_targets=[],
        inspection_sinks=["Browse"],
        output_schemas={},
        output_grain=["UNKNOWN"],
        tool_types=["DbFileInput", "BrowseV2"],
        transformation_signatures=[],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=[],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=2,
        edge_count=1,
        dag_depth=1,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "BrowseV2"],
        complexity_level="LOW",
        complexity_score=10.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "id": ColumnEvidence(original_name="id", normalized_name="id", source_dataset="input.csv", provenance="Input", is_required=True),
            "amount": ColumnEvidence(original_name="amount", normalized_name="amount", source_dataset="input.csv", provenance="Input", is_required=True),
            "missing_col": ColumnEvidence(original_name="missing_col", normalized_name="missing_col", source_dataset="input.csv", provenance="Input", is_required=True),
        },
        required_columns=["id", "amount", "missing_col"],
        available_columns=["id", "amount", "missing_col"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[],
    )

    fp_target = WorkflowFingerprint(
        workflow_id="tgt_1",
        workflow_name="target_wf",
        sources=["input.csv"],
        source_types={"input.csv": "FILE"},
        source_fields={"input.csv": ["id", "amount"]},
        production_targets=["output.yxdb"],
        inspection_sinks=[],
        output_schemas={"output.yxdb": ["id", "amount"]},
        output_grain=["UNKNOWN"],
        tool_types=["DbFileInput", "DbFileOutput"],
        transformation_signatures=[],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=[],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=2,
        edge_count=1,
        dag_depth=1,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "DbFileOutput"],
        complexity_level="LOW",
        complexity_score=10.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "id": ColumnEvidence(original_name="id", normalized_name="id", source_dataset="input.csv", provenance="Input", is_required=True),
            "amount": ColumnEvidence(original_name="amount", normalized_name="amount", source_dataset="input.csv", provenance="Input", is_required=True),
        },
        required_columns=["id", "amount"],
        available_columns=["id", "amount"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[],
    )

    comp = compare_workflows(fp_source, fp_target)
    subsumed, ev = evaluate_directional_data_subsumption(fp_source, fp_target, comp)

    assert subsumed is False
    assert ev.missing_fields_count == 1
    assert "missing_col" in ev.missing_fields
