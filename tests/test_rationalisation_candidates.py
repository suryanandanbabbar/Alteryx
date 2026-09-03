"""Deterministic unit tests for Candidate Detection and Safety Gates in ETL Rationalisation."""

from __future__ import annotations

import pytest

from awa.analysis.rationalisation_analyzer import (
    compare_workflows,
    detect_candidate_from_comparison,
    evaluate_consolidation_rules,
    ConsolidationRules,
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
    frequency: str = "Daily",
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
        frequency=frequency,
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
        """High source overlap + high logic overlap + distinct targets + Low complexity -> CONSOLIDATE."""
        trans = ["Filter: active=true", "Join on customerid", "Formula: total=qty*price"]
        fp_a = _make_fp("wf_a", "Monthly_Sales.yxmd", ["customers.xlsx", "orders.csv"], ["monthly_sales.yxdb"], trans, complexity="LOW")
        fp_b = _make_fp("wf_b", "Regional_Sales.yxmd", ["customers.xlsx", "orders.csv"], ["regional_sales.yxdb"], trans, complexity="MEDIUM")

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

    # -----------------------------------------------------------------------
    # Consolidation / Merge Rules Tests (Rules A, B, C, D)
    # -----------------------------------------------------------------------
    def test_rule_a_same_sources_same_frequency_one_low_complexity_merges(self):
        """Rule A: 100% source overlap + at least one Low complexity + same frequency -> MERGE."""
        trans = ["Filter: region='US'"]
        fp_a = _make_fp("wf_1", "Orders_Cleanse.yxmd", ["raw_orders.csv", "customers.xlsx"], ["orders_clean.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "Orders_Summarize.yxmd", ["raw_orders.csv", "customers.xlsx"], ["orders_agg.yxdb"], trans, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_A
        assert decision.is_source_100_pct is True
        assert decision.is_same_frequency is True
        assert decision.complexity_a == "LOW"
        assert decision.merge_direction == "Orders_Summarize.yxmd absorbs Orders_Cleanse.yxmd"
        assert len(decision.evidence) >= 4

    def test_rule_a_same_sources_same_frequency_both_medium_high_does_not_merge(self):
        """Same sources + same frequency + both Medium/High complexity -> DO NOT MERGE."""
        trans = ["Filter: x=1"]
        fp_a = _make_fp("wf_1", "Pricing_Engine.yxmd", ["sales_raw.csv"], ["pricing_out.yxdb"], trans, complexity="HIGH", frequency="Daily")
        fp_b = _make_fp("wf_2", "Risk_Model.yxmd", ["sales_raw.csv"], ["risk_out.yxdb"], trans, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "DO NOT MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_C
        assert "Medium or High complexity" in decision.reason

    def test_rule_a_partial_source_overlap_does_not_qualify(self):
        """Partial source overlap + same frequency + one Low -> does NOT qualify under Rule A."""
        trans = ["Filter: x=1"]
        fp_a = _make_fp("wf_1", "A.yxmd", ["shared.csv", "unique_a.csv"], ["out_a.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "B.yxmd", ["shared.csv", "unique_b.csv"], ["out_b.yxdb"], trans, complexity="LOW", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        # Rule A requires 100% source overlap (identical set). Here it's 33% (1/3).
        # Rule B applies if outputs differ, one is Low, same frequency!
        assert decision.is_source_100_pct is False

    def test_rule_b_different_outputs_same_frequency_one_low_complexity_merges(self):
        """Rule B: Different outputs + at least one Low complexity + same frequency -> MERGE."""
        trans = ["Filter: status='A'"]
        fp_a = _make_fp("wf_1", "Policy_Feed.yxmd", ["policy_in.csv"], ["policy_active.yxdb"], trans, complexity="LOW", frequency="Weekly")
        fp_b = _make_fp("wf_2", "Policy_Archive.yxmd", ["archive_in.csv"], ["policy_archive.yxdb"], trans, complexity="MEDIUM", frequency="Weekly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_B
        assert decision.output_relationship == "DIFFERENT"
        assert decision.is_same_frequency is True

    def test_rule_c_different_outputs_both_medium_high_complexity_do_not_merge(self):
        """Rule C: Different outputs + both Medium/High complexity -> DO NOT MERGE."""
        trans = ["Formula: calc()"]
        fp_a = _make_fp("wf_1", "Underwriting_Rules.yxmd", ["app.csv"], ["decisions.yxdb"], trans, complexity="HIGH", frequency="Monthly")
        fp_b = _make_fp("wf_2", "Claims_Fraud.yxmd", ["claims.csv"], ["fraud_alerts.yxdb"], trans, complexity="MEDIUM", frequency="Monthly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "DO NOT MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_C
        assert decision.merge_direction is None

    def test_rule_b_different_outputs_different_frequency_does_not_qualify(self):
        """Different outputs + different frequency -> does NOT qualify under Rule B."""
        trans = ["Formula: calc()"]
        fp_a = _make_fp("wf_1", "Daily_Sales.yxmd", ["s1.csv"], ["out_1.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "Monthly_Sales.yxmd", ["s2.csv"], ["out_2.yxdb"], trans, complexity="LOW", frequency="Monthly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "DO NOT MERGE"
        assert decision.is_same_frequency is False
        assert decision.matched_rule == ConsolidationRules.RULE_DEFAULT

    def test_upstream_downstream_relationship_alone_does_not_satisfy_rule_d(self):
        """Test 8: Upstream/downstream relationship alone does NOT satisfy Rule D."""
        trans_a = ["Filter: region='US'"]
        trans_b = ["Formula: tax=0.15"]
        # Workflow A produces 'intermediate.yxdb', which Workflow B consumes as a source, but neither subsumes the other
        fp_a = _make_fp("wf_a", "Stage1.yxmd", ["raw.csv"], ["intermediate.yxdb"], trans_a, complexity="MEDIUM", frequency="Daily")
        fp_b = _make_fp("wf_b", "Stage2.yxmd", ["intermediate.yxdb"], ["final.yxdb"], trans_b, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.logic_preservable is False
        assert decision.matched_rule != ConsolidationRules.RULE_D

    def test_rule_d_logic_preservation_supported_by_subsumption(self):
        """Test 10: Logic preservation explicitly proven by deterministic subsumption -> MERGE."""
        trans_a = ["Filter: active=1", "Formula: total=qty*price", "Join on id"]
        trans_b = ["Filter: active=1", "Formula: total=qty*price"]
        fp_a = _make_fp("wf_a", "Full_Pipeline.yxmd", ["data.csv"], ["target1.yxdb", "target2.yxdb"], trans_a, complexity="MEDIUM")
        fp_b = _make_fp("wf_b", "Partial_Pipeline.yxmd", ["data.csv"], ["target1.yxdb"], trans_b, complexity="LOW")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "MERGE"
        assert decision.logic_preservable is True
        assert decision.matched_rule == ConsolidationRules.RULE_D
        assert decision.merge_direction == "Full_Pipeline.yxmd absorbs Partial_Pipeline.yxmd"

    def test_rule_d_unsupported_logic_preservation_not_claimed(self):
        """Test 11: When logic preservation cannot be proven, Rule D must be false."""
        trans_a = ["Filter: country='UK'"]
        trans_b = ["Filter: country='FR'"]
        fp_a = _make_fp("wf_a", "UK_ETL.yxmd", ["uk_raw.csv"], ["uk_out.yxdb"], trans_a, complexity="HIGH", frequency="Monthly")
        fp_b = _make_fp("wf_b", "FR_ETL.yxmd", ["fr_raw.csv"], ["fr_out.yxdb"], trans_b, complexity="HIGH", frequency="Monthly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.logic_preservable is False
        assert decision.matched_rule != ConsolidationRules.RULE_D

    def test_empty_source_sets_do_not_qualify_as_100_percent_overlap(self):
        """Empty source sets must not accidentally qualify as 100% overlap."""
        trans = ["Filter: x=1"]
        fp_a = _make_fp("wf_a", "No_Source_A.yxmd", [], ["out.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_b", "No_Source_B.yxmd", [], ["out.yxdb"], trans, complexity="LOW", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.is_source_100_pct is False
        assert decision.matched_rule != ConsolidationRules.RULE_A

    def test_physical_source_identities_used_not_captions(self):
        """Physical configured file paths are normalized and compared, ignoring display wrappers."""
        fp_a = _make_fp("wf_a", "W1.yxmd", ["C:\\Data\\Input\\Claims_Data.xlsx"], ["Out1.yxdb"], ["Filter: 1=1"], complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_b", "W2.yxmd", ["/var/data/input/claims_data.xlsx"], ["Out2.yxdb"], ["Filter: 1=1"], complexity="LOW", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.is_source_100_pct is True
        assert decision.matched_rule == ConsolidationRules.RULE_A
        assert decision.recommendation == "MERGE"

    def test_no_workflow_name_hardcoding(self):
        """Rules execute identically regardless of arbitrary/random workflow names."""
        fp_a = _make_fp("wf_rand1", "ZZZ_999.yxmd", ["input.csv"], ["t1.yxdb"], ["Filter: a=1"], complexity="LOW", frequency="Weekly")
        fp_b = _make_fp("wf_rand2", "AAA_000.yxmd", ["input.csv"], ["t2.yxdb"], ["Filter: a=1"], complexity="HIGH", frequency="Weekly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_A
        assert decision.merge_direction == "AAA_000.yxmd absorbs ZZZ_999.yxmd"

    def test_repeatable_deterministic_recommendations(self):
        """Identical canonical inputs always produce the exact same recommendation."""
        fp_a = _make_fp("wf_1", "Test_A.yxmd", ["feed.csv"], ["target.yxdb"], ["Filter: a=1"], complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "Test_B.yxmd", ["feed.csv"], ["target.yxdb"], ["Filter: a=1"], complexity="LOW", frequency="Daily")

        comp1 = compare_workflows(fp_a, fp_b)
        comp2 = compare_workflows(fp_a, fp_b)

        d1 = evaluate_consolidation_rules(fp_a, fp_b, comp1)
        d2 = evaluate_consolidation_rules(fp_a, fp_b, comp2)

        assert d1.to_dict() == d2.to_dict()

    # --- Comprehensive Test Cases 1 through 17 ---

    def test_case_1_same_4_sources_same_frequency_one_low_merges(self):
        """Test 1: Same 4 sources + same frequency + one Low -> MERGE."""
        sources = ["s1.csv", "s2.csv", "s3.csv", "s4.csv"]
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", sources, ["out1.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", sources, ["out2.yxdb"], trans, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_A
        assert cand is not None
        assert cand.recommendation_type == "CONSOLIDATE"

    def test_case_2_same_sources_different_frequency_not_consolidate(self):
        """Test 2: Same sources + different frequency -> DO NOT RENDER as Consolidate candidate."""
        sources = ["s1.csv", "s2.csv"]
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", sources, ["out1.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", sources, ["out2.yxdb"], trans, complexity="LOW", frequency="Weekly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "DO NOT MERGE"
        # If surfaced as a candidate, recommendation_type CANNOT be CONSOLIDATE
        if cand is not None:
            assert cand.recommendation_type != "CONSOLIDATE"

    def test_case_3_same_sources_same_frequency_both_high_not_consolidate(self):
        """Test 3: Same sources + same frequency + both High -> DO NOT RENDER as Consolidate candidate."""
        sources = ["s1.csv", "s2.csv"]
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", sources, ["out1.yxdb"], trans, complexity="HIGH", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", sources, ["out2.yxdb"], trans, complexity="HIGH", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "DO NOT MERGE"
        if cand is not None:
            assert cand.recommendation_type != "CONSOLIDATE"

    def test_case_4_different_outputs_same_frequency_one_low_merges(self):
        """Test 4: Different outputs + substantive commonality + same frequency + at least one Low -> MERGE."""
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", ["shared.csv"], ["out_a.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["shared.csv"], ["out_b.yxdb"], trans, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "MERGE"
        assert decision.matched_rule in (ConsolidationRules.RULE_A, ConsolidationRules.RULE_B)
        assert cand is not None
        assert cand.recommendation_type == "CONSOLIDATE"

    def test_case_5_different_outputs_different_frequency_one_low_not_consolidate(self):
        """Test 5: Different outputs + different frequency + at least one Low -> DO NOT RENDER as Consolidate candidate."""
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", ["shared.csv"], ["out_a.yxdb"], trans, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["shared.csv"], ["out_b.yxdb"], trans, complexity="LOW", frequency="Monthly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "DO NOT MERGE"
        if cand is not None:
            assert cand.recommendation_type != "CONSOLIDATE"

    def test_case_6_different_outputs_both_medium_high_do_not_merge(self):
        """Test 6: Different outputs + both Medium/High -> DO NOT MERGE (Rule C)."""
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", ["src_a.csv"], ["out_a.yxdb"], trans, complexity="HIGH", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["src_b.csv"], ["out_b.yxdb"], trans, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        assert decision.recommendation == "DO NOT MERGE"
        assert decision.matched_rule == ConsolidationRules.RULE_C
        if cand is not None:
            assert cand.recommendation_type != "CONSOLIDATE"

    def test_case_7_zero_overlap_low_high_complexity_strictly_suppressed(self):
        """Test 7: 0% source + 0% target + 0% frequency + 0% logic + low/high complexity -> DO NOT RENDER (None)."""
        trans_a = ["Filter: region='US'"]
        trans_b = ["Formula: tax=0.2"]
        fp_a = _make_fp("wf_1", "BBCFoodAggr.ymlx", ["in_a.csv"], ["out_a.yxdb"], trans_a, complexity="LOW", frequency="Not documented")
        fp_b = _make_fp("wf_2", "BBCFood v2.ymlx", ["in_b.csv"], ["out_b.yxdb"], trans_b, complexity="HIGH", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        # Must return None so unrelated workflows are completely excluded
        assert cand is None

    def test_case_9_dag_similarity_alone_never_sufficient(self):
        """Test 9: Low or high DAG similarity alone is never sufficient to qualify as MERGE."""
        trans_a = ["Filter: region='US'"]
        trans_b = ["Formula: tax=0.2"]
        # Same node/edge structure, 100% DAG similarity, but 0% source/target/logic and differing frequency
        fp_a = _make_fp("wf_1", "W1.yxmd", ["in_a.csv"], ["out_a.yxdb"], trans_a, complexity="HIGH", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["in_b.csv"], ["out_b.yxdb"], trans_b, complexity="HIGH", frequency="Monthly")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert decision.recommendation == "DO NOT MERGE"

    def test_case_12_not_documented_vs_daily_is_frequency_mismatch(self):
        """Test 12: 'Not documented' frequency versus 'Daily' -> frequency mismatch (overlap = 0.0)."""
        trans = ["Filter: a=1"]
        fp_a = _make_fp("wf_1", "W1.yxmd", ["s1.csv"], ["t1.yxdb"], trans, frequency="Not documented")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["s2.csv"], ["t2.yxdb"], trans, frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

        assert comp.metrics.frequency_overlap == 0.0
        assert decision.is_same_frequency is False
        assert decision.recommendation == "DO NOT MERGE"

    def test_case_17_no_false_rationale_contradicting_metrics(self):
        """Test 17: Rationale never claims shared sources when source overlap is 0%."""
        trans_a = ["Filter: region='US'"]
        trans_b = ["Formula: tax=0.2"]
        fp_a = _make_fp("wf_1", "W1.yxmd", ["in_a.csv"], ["out_a.yxdb"], trans_a, complexity="LOW", frequency="Daily")
        fp_b = _make_fp("wf_2", "W2.yxmd", ["in_b.csv"], ["out_b.yxdb"], trans_b, complexity="MEDIUM", frequency="Daily")

        comp = compare_workflows(fp_a, fp_b)
        cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

        if cand is not None:
            assert "()" not in cand.reasoning
            assert "identical source" not in cand.reasoning.lower()



