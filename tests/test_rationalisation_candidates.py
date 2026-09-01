"""Deterministic unit tests for Candidate Detection and Safety Gates in ETL Rationalisation."""

from __future__ import annotations

import pytest

from awa.analysis.rationalisation_analyzer import (
    compare_workflows,
    detect_candidate_from_comparison,
    RationalisationThresholds,
)
from awa.model.portfolio import (
    DeterministicMetrics,
    WorkflowFingerprint,
)


def _make_fp(
    wid: str,
    name: str,
    sources: list[str],
    targets: list[str],
    transformations: list[str],
    schemas: dict[str, list[str]] | None = None,
    grain: list[str] | None = None,
    consumers: list[str] | None = None,
    complexity: str = "MEDIUM",
    criticality: str = "MEDIUM",
) -> WorkflowFingerprint:
    """Convenient helper to build a WorkflowFingerprint for testing comparisons."""
    target_schemas = schemas or {t: ["col1", "col2", "col3"] for t in targets}
    return WorkflowFingerprint(
        workflow_id=wid,
        workflow_name=name,
        sources=sources,
        production_targets=targets,
        inspection_sinks=[],
        output_schemas=target_schemas,
        output_grain=grain or ["customer_id"],
        tool_types=["InputData", "Filter", "Formula", "OutputData"],
        transformation_signatures=transformations,
        filters=[t for t in transformations if "filter" in t.lower()],
        join_keys=[t for t in transformations if "join" in t.lower()],
        aggregations=[],
        formulas=[t for t in transformations if "formula" in t.lower()],
        node_count=10,
        edge_count=10,
        dag_depth=4,
        branch_points=1,
        merge_points=1,
        complexity_level=complexity,
        complexity_score=50.0,
        criticality_level=criticality,
        criticality_score=50.0,
        downstream_consumers=consumers or [],
    )


class TestRationalisationCandidates:
    """Test candidate detection rules, safety gates, and suppression of NO_ACTION."""

    def test_retire_candidate_when_all_safety_gates_pass(self):
        """Identical targets, high logic similarity, identical schema & grain, 0 consumers -> RETIRE_CANDIDATE."""
        shared_trans = ["Filter: active=true", "Formula: total=qty*price", "Join on customerid"]
        fp_a = _make_fp("wf_a", "Sales_Report_V1.yxmd", ["sales.csv"], ["sales_report.yxdb"], shared_trans)
        fp_b = _make_fp("wf_b", "Sales_Report_V2.yxmd", ["sales.csv"], ["sales_report.yxdb"], shared_trans)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        assert cand.recommendation_type == "RETIRE_CANDIDATE"
        assert "RETIRE_CANDIDATE" in cand.admissible_recommendations
        assert cand.opportunity_score >= 80.0
        assert "operational scheduling" in cand.proposed_strategy.lower()
        # Verify validation requirements exist
        assert len(cand.validation_requirements) >= 3

    def test_retire_rejected_when_output_schemas_differ(self):
        """If output schemas differ materially, retirement safety gate must block RETIRE_CANDIDATE."""
        shared_trans = ["Filter: active=true", "Formula: total=qty*price", "Join on customerid"]
        fp_a = _make_fp("wf_a", "A.yxmd", ["sales.csv"], ["report.yxdb"], shared_trans, schemas={"report.yxdb": ["A", "B", "C"]})
        fp_b = _make_fp("wf_b", "B.yxmd", ["sales.csv"], ["report.yxdb"], shared_trans, schemas={"report.yxdb": ["X", "Y", "Z"]})

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        # Must be rejected from RETIRE_CANDIDATE, falls back to CONSOLIDATE or REVIEW
        assert cand.recommendation_type != "RETIRE_CANDIDATE"

    def test_retire_rejected_when_downstream_consumers_exist(self):
        """If a workflow has known downstream consumers, retirement safety gate must block RETIRE_CANDIDATE."""
        shared_trans = ["Filter: active=true", "Formula: total=qty*price", "Join on customerid"]
        # Workflow A produces an asset ingested by Workflow C!
        fp_a = _make_fp("wf_a", "Producer_A.yxmd", ["sales.csv"], ["report.yxdb"], shared_trans, consumers=["Consumer_C.yxmd"])
        fp_b = _make_fp("wf_b", "Producer_B.yxmd", ["sales.csv"], ["report.yxdb"], shared_trans)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        # Downstream consumer blocks retirement candidate!
        assert cand.recommendation_type != "RETIRE_CANDIDATE"

    def test_retire_rejected_when_material_unique_logic_exists(self):
        """If one workflow contains significant unique transformation logic, cannot retire."""
        trans_a = ["Filter: active=true", "Join on customerid", "Formula: risk_score=calc()", "Spatial: distance_match()", "Python: ml_model()"]
        trans_b = ["Filter: active=true", "Join on customerid"]
        fp_a = _make_fp("wf_a", "Complex_A.yxmd", ["sales.csv"], ["report.yxdb"], trans_a)
        fp_b = _make_fp("wf_b", "Simple_B.yxmd", ["sales.csv"], ["report.yxdb"], trans_b)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        assert cand.recommendation_type != "RETIRE_CANDIDATE"

    def test_consolidate_candidate_with_distinct_outputs(self):
        """High source overlap + high logic overlap + distinct targets -> CONSOLIDATE."""
        trans = ["Filter: active=true", "Join on customerid", "Formula: total=qty*price"]
        fp_a = _make_fp("wf_a", "Monthly_Sales.yxmd", ["customers.xlsx", "orders.csv"], ["monthly_sales.yxdb"], trans)
        fp_b = _make_fp("wf_b", "Regional_Sales.yxmd", ["customers.xlsx", "orders.csv"], ["regional_sales.yxdb"], trans)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        assert cand.recommendation_type == "CONSOLIDATE"
        assert "CONSOLIDATE" in cand.admissible_recommendations
        assert "RETIRE_CANDIDATE" not in cand.admissible_recommendations
        assert "centralize" in cand.proposed_strategy.lower()

    def test_shared_logic_candidate_with_different_sources(self):
        """Meaningful transformation overlap with different sources/targets -> SHARED_LOGIC."""
        trans = ["Filter: valid_account=1", "Formula: calculate_tax()", "Join on account_id"]
        fp_a = _make_fp("wf_a", "Retail_Tax.yxmd", ["retail_data.csv"], ["retail_tax.yxdb"], trans)
        fp_b = _make_fp("wf_b", "Commercial_Tax.yxmd", ["commercial_data.csv"], ["commercial_tax.yxdb"], trans)

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert cand is not None
        assert cand.recommendation_type == "SHARED_LOGIC"
        assert "SHARED_LOGIC" in cand.admissible_recommendations
        assert "reusable" in cand.proposed_strategy.lower() or "macro" in cand.proposed_strategy.lower()

    def test_no_action_suppressed_from_candidates(self):
        """Workflows with minimal or coincidental overlap must return None (NO_ACTION suppressed)."""
        fp_a = _make_fp("wf_a", "Claims_Processor.yxmd", ["claims_feed.csv"], ["claims.yxdb"], ["Filter: claim_status=open"])
        fp_b = _make_fp("wf_b", "Employee_Directory.yxmd", ["hr_roster.xlsx"], ["roster.yxdb"], ["Formula: fullname=first+last"])

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        # Strictly suppressed! Must not pollute the UI with thousands of empty cards.
        assert cand is None

    def test_opportunity_score_clamping_and_determinism(self):
        """Opportunity score must be clamped strictly within [0.0, 100.0] and reproducible."""
        trans = ["Filter: a=1", "Formula: b=2"]
        fp_a = _make_fp("wf_a", "A.yxmd", ["s1.csv"], ["t1.yxdb"], trans)
        fp_b = _make_fp("wf_b", "B.yxmd", ["s1.csv"], ["t1.yxdb"], trans)

        comp1 = compare_workflows(fp_a, fp_b)
        comp2 = compare_workflows(fp_a, fp_b)

        assert 0.0 <= comp1.opportunity_score <= 100.0
        assert comp1.opportunity_score == comp2.opportunity_score
