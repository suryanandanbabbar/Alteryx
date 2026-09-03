"""Deterministic unit tests for 5-Factor Workflow Criticality Engine.

Criticality
• Technical Factors
  • Number of downstream outputs
  • Number of upstream sources
  • Number of ETL workflows consuming the output of this workflow
• Operational Factors
  • Last Run
  • Frequency
* Business impact factors can be added further once the information about downstream targets/consumers is available
"""

from __future__ import annotations

import pytest

from awa.analysis.workflow_criticality import (
    calculate_workflow_criticality,
    normalize_downstream_outputs_score,
    normalize_upstream_sources_score,
    normalize_etl_consumers_score,
    normalize_last_run_score,
    normalize_frequency_score,
    PortfolioDependencyContext,
    CRITICALITY_FACTOR_WEIGHT,
    TECHNICAL_WEIGHT_TOTAL,
    OPERATIONAL_WEIGHT_TOTAL,
    CRITICALITY_LOW_MAX,
    CRITICALITY_MEDIUM_MAX,
    BUSINESS_IMPACT_NOTE,
)


class TestFiveFactorCriticalityEngine:
    def test_weight_constants_integrity(self):
        """Each factor must be 20%, Technical 60%, Operational 40%."""
        assert CRITICALITY_FACTOR_WEIGHT == 0.20
        assert TECHNICAL_WEIGHT_TOTAL == 0.60
        assert OPERATIONAL_WEIGHT_TOTAL == 0.40
        assert TECHNICAL_WEIGHT_TOTAL + OPERATIONAL_WEIGHT_TOTAL == 1.00

    def test_deterministic_reproducibility(self):
        """Same evidence must produce exactly the same score, level, and breakdown on repeated runs."""
        kwargs = dict(
            workflow_id="wf_001",
            workflow_filename="Customer_Billing.yxmd",
            sources=["Billing_In.xlsx", "Rates.csv"],
            targets=["Invoices.xlsx", "Ledger.yxdb"],
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )
        res1 = calculate_workflow_criticality(**kwargs)
        res2 = calculate_workflow_criticality(**kwargs)

        assert res1.score == res2.score
        assert res1.level == res2.level
        assert res1.technical_score == res2.technical_score
        assert res1.operational_score == res2.operational_score
        assert res1.factors == res2.factors
        assert res1.factor_breakdown == res2.factor_breakdown
        assert res1.criticality_justification == res2.criticality_justification
        assert res1.business_impact_note == BUSINESS_IMPACT_NOTE

    def test_five_factor_weightage_formula(self):
        """Verify the exact mathematical calculation: each factor contributes factor_score * 0.20."""
        # 2 outputs (70.0), 2 sources (70.0), 1 consumer (60.0) -> Tech = (70+70+60)*0.20 = 40.0
        # Last Run: "5 months ago" (40.0), Frequency: "Monthly" (60.0) -> Oper = (40+60)*0.20 = 20.0
        # Final Score = 40.0 + 20.0 = 60.0 -> MEDIUM
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                "Out1.yxdb": [("wf_downstream", "Downstream.yxmd")],
            }
        )
        res = calculate_workflow_criticality(
            workflow_id="wf_main",
            workflow_filename="Main.yxmd",
            sources=["Src1.xlsx", "Src2.csv"],
            targets=["Out1.yxdb", "Out2.yxdb"],
            context=dep_ctx,
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )

        assert res.breakdown["downstream_outputs"] == 70.0
        assert res.breakdown["upstream_sources"] == 70.0
        assert res.breakdown["etl_consumers"] == 60.0
        assert res.breakdown["last_run"] == 40.0
        assert res.breakdown["frequency"] == 60.0

        assert res.technical_score == 40.0
        assert res.operational_score == 20.0
        assert res.score == 60.0
        assert res.level == "MEDIUM"

    def test_subtotals_and_bounds(self):
        """Technical subtotal is exactly 60% max, Operational 40% max, Total 100% max."""
        # Max out all factors (5+ outputs, 5+ sources, 5+ consumers, today, realtime)
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                f"out_{i}.yxdb": [(f"c_{j}", f"C{j}.yxmd") for j in range(5)]
                for i in range(5)
            }
        )
        res = calculate_workflow_criticality(
            workflow_id="wf_max",
            workflow_filename="Max.yxmd",
            sources=["s1", "s2", "s3", "s4", "s5", "s6"],
            targets=["out_0.yxdb", "out_1.yxdb", "out_2.yxdb", "out_3.yxdb", "out_4.yxdb", "out_5.yxdb"],
            context=dep_ctx,
            operational_metadata={"last_run": "today", "frequency": "Real-time"},
        )
        assert res.technical_score == 60.0
        assert res.operational_score == 40.0
        assert res.score == 100.0
        assert res.level == "HIGH"
        assert 0.0 <= res.score <= 100.0

    def test_missing_and_unknown_evidence_handled_explicitly(self):
        """Missing or unknown evidence is deterministically scored as 0.0 without hallucination."""
        res = calculate_workflow_criticality(
            workflow_id="wf_empty",
            workflow_filename="Empty.yxmd",
            sources=[],
            targets=[],
            inspection_sinks=["BrowseV2"],
            operational_metadata=None,
        )
        assert res.breakdown["downstream_outputs"] == 0.0
        assert res.breakdown["upstream_sources"] == 0.0
        assert res.breakdown["etl_consumers"] == 0.0
        assert res.breakdown["last_run"] == 0.0
        assert res.breakdown["frequency"] == 0.0
        assert res.technical_score == 0.0
        assert res.operational_score == 0.0
        assert res.score == 0.0
        assert res.level == "LOW"

        # Check factor item raw evidence
        assert res.factor_breakdown["last_run"]["raw_evidence"] == "Not documented"
        assert res.factor_breakdown["frequency"]["raw_evidence"] == "Not documented"

    def test_last_run_parsing_examples(self):
        """Test Last Run parsing across recent and older runs (including ~5 months ago)."""
        score_recent, raw_recent = normalize_last_run_score("today")
        assert score_recent == 100.0
        assert raw_recent == "today"

        score_yesterday, raw_yesterday = normalize_last_run_score("yesterday")
        assert score_yesterday == 100.0

        score_days, _ = normalize_last_run_score("3 days ago")
        assert score_days == 100.0

        score_1mo, _ = normalize_last_run_score("1 month ago")
        assert score_1mo == 80.0

        score_2mo, _ = normalize_last_run_score("2 months ago")
        assert score_2mo == 60.0

        score_5mo, raw_5mo = normalize_last_run_score("5 months ago")
        assert score_5mo == 40.0
        assert raw_5mo == "5 months ago"

        score_1yr, _ = normalize_last_run_score("1 year ago")
        assert score_1yr == 20.0

        score_none, raw_none = normalize_last_run_score(None)
        assert score_none == 0.0
        assert raw_none == "Not documented"

    def test_frequency_parsing_examples(self):
        """Test Frequency parsing across schedules (including Monthly)."""
        score_rt, _ = normalize_frequency_score("Continuous")
        assert score_rt == 100.0

        score_daily, _ = normalize_frequency_score("Daily")
        assert score_daily == 90.0

        score_weekly, _ = normalize_frequency_score("Weekly")
        assert score_weekly == 75.0

        score_monthly, raw_monthly = normalize_frequency_score("Monthly")
        assert score_monthly == 60.0
        assert raw_monthly == "Monthly"

        score_quarterly, _ = normalize_frequency_score("Quarterly")
        assert score_quarterly == 45.0

        score_annually, _ = normalize_frequency_score("Annually")
        assert score_annually == 20.0

        score_adhoc, _ = normalize_frequency_score("Ad-hoc")
        assert score_adhoc == 15.0

        score_none, raw_none = normalize_frequency_score(None)
        assert score_none == 0.0
        assert raw_none == "Not documented"

    def test_factor_isolation_downstream_outputs(self):
        """Changing downstream-output count affects only the downstream-output factor."""
        base_kwargs = dict(
            workflow_id="wf_iso",
            workflow_filename="Iso.yxmd",
            sources=["s1.csv"],
            targets=["t1.yxdb"],
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )
        res1 = calculate_workflow_criticality(**base_kwargs)

        # Change ONLY targets
        res2 = calculate_workflow_criticality(
            **{**base_kwargs, "targets": ["t1.yxdb", "t2.yxdb", "t3.yxdb"]}
        )

        assert res2.breakdown["downstream_outputs"] > res1.breakdown["downstream_outputs"]
        assert res2.breakdown["upstream_sources"] == res1.breakdown["upstream_sources"]
        assert res2.breakdown["etl_consumers"] == res1.breakdown["etl_consumers"]
        assert res2.breakdown["last_run"] == res1.breakdown["last_run"]
        assert res2.breakdown["frequency"] == res1.breakdown["frequency"]

    def test_factor_isolation_upstream_sources(self):
        """Changing upstream-source count affects only the upstream-source factor."""
        base_kwargs = dict(
            workflow_id="wf_iso",
            workflow_filename="Iso.yxmd",
            sources=["s1.csv"],
            targets=["t1.yxdb"],
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )
        res1 = calculate_workflow_criticality(**base_kwargs)

        # Change ONLY sources
        res2 = calculate_workflow_criticality(
            **{**base_kwargs, "sources": ["s1.csv", "s2.csv", "s3.csv"]}
        )

        assert res2.breakdown["upstream_sources"] > res1.breakdown["upstream_sources"]
        assert res2.breakdown["downstream_outputs"] == res1.breakdown["downstream_outputs"]
        assert res2.breakdown["etl_consumers"] == res1.breakdown["etl_consumers"]
        assert res2.breakdown["last_run"] == res1.breakdown["last_run"]
        assert res2.breakdown["frequency"] == res1.breakdown["frequency"]

    def test_factor_isolation_etl_consumers(self):
        """Changing ETL-consumer count affects only the ETL-consumer factor."""
        base_kwargs = dict(
            workflow_id="wf_iso",
            workflow_filename="Iso.yxmd",
            sources=["s1.csv"],
            targets=["t1.yxdb"],
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )
        res1 = calculate_workflow_criticality(**base_kwargs)

        # Add portfolio consumer context
        dep_ctx = PortfolioDependencyContext(
            source_to_consumers={
                "t1.yxdb": [("wf_other1", "Other1.yxmd"), ("wf_other2", "Other2.yxmd")],
            }
        )
        res2 = calculate_workflow_criticality(**{**base_kwargs, "context": dep_ctx})

        assert res2.breakdown["etl_consumers"] > res1.breakdown["etl_consumers"]
        assert res2.breakdown["downstream_outputs"] == res1.breakdown["downstream_outputs"]
        assert res2.breakdown["upstream_sources"] == res1.breakdown["upstream_sources"]
        assert res2.breakdown["last_run"] == res1.breakdown["last_run"]
        assert res2.breakdown["frequency"] == res1.breakdown["frequency"]

    def test_audit_dictionary_and_required_note(self):
        """Audit dictionary must expose all 5 factor details and the exact business impact note."""
        res = calculate_workflow_criticality(
            workflow_id="wf_audit",
            workflow_filename="Audit.yxmd",
            sources=["in.csv"],
            targets=["out.yxdb"],
            operational_metadata={"last_run": "1 month ago", "frequency": "Daily"},
        )
        d = res.to_dict()

        assert d["criticality_source"] == "deterministic"
        assert d["source"] == "deterministic"
        assert d["business_impact_note"] == BUSINESS_IMPACT_NOTE
        assert len(d["factors"]) == 5
        assert len(d["factor_breakdown"]) == 5

        for factor_key in ["downstream_outputs", "upstream_sources", "etl_consumers", "last_run", "frequency"]:
            item = d["factor_breakdown"][factor_key]
            assert "name" in item
            assert "category" in item
            assert item["weight_pct"] == 20.0
            assert "raw_evidence" in item
            assert "factor_score" in item
            assert "weighted_contribution_pct" in item

    def test_exact_canonical_factor_names_and_no_example_leakage(self):
        """Canonical factor names must be clean without example strings leaking into names."""
        res = calculate_workflow_criticality(
            workflow_id="wf_clean_names",
            workflow_filename="CleanNames.yxmd",
            sources=["in.csv"],
            targets=["out.yxdb"],
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )

        fb = res.factor_breakdown
        assert fb["downstream_outputs"]["name"] == "Downstream outputs"
        assert fb["upstream_sources"]["name"] == "Upstream sources"
        assert fb["etl_consumers"]["name"] == "ETL workflow consumers"
        assert fb["last_run"]["name"] == "Last Run"
        assert fb["frequency"]["name"] == "Frequency"

        # Check raw_evidence / raw_value has the values
        assert fb["last_run"]["raw_evidence"] == "5 months ago"
        assert fb["frequency"]["raw_evidence"] == "Monthly"
        assert fb["downstream_outputs"]["raw_value"] == 1
        assert fb["upstream_sources"]["raw_value"] == 1
        assert fb["etl_consumers"]["raw_value"] == 0

        # Check factors array strings
        assert "Last Run -> Value: 5 months ago" in res.factors[3]
        assert "Frequency -> Value: Monthly" in res.factors[4]

        # Ensure no illustrative example prefixes leak into factor names
        for item in fb.values():
            assert "Ex:" not in item["name"]
            assert "(20%)" not in item["name"]
            assert "(60%)" not in item["name"]
            assert "(40%)" not in item["name"]

        for f in res.factors:
            assert "Ex:" not in f

    def test_dynamic_downstream_outputs_evidence_variation(self):
        """Changing downstream outputs changes the calculated count, value, score, and contribution."""
        # 1 output
        res1 = calculate_workflow_criticality(
            workflow_id="wf_dyn_out_1",
            workflow_filename="DynOut1.yxmd",
            sources=["input.csv"],
            targets=["Sales_Report.xlsx"],
        )
        fb1 = res1.factor_breakdown["downstream_outputs"]
        assert fb1["raw_value"] == 1
        assert fb1["raw_evidence"] == "1 downstream output"
        assert fb1["factor_score"] == 40.0
        assert fb1["weighted_contribution_pct"] == 8.0

        # 3 outputs
        res3 = calculate_workflow_criticality(
            workflow_id="wf_dyn_out_3",
            workflow_filename="DynOut3.yxmd",
            sources=["input.csv"],
            targets=["Sales_Report.xlsx", "Summary.csv", "Metrics.yxdb"],
        )
        fb3 = res3.factor_breakdown["downstream_outputs"]
        assert fb3["raw_value"] == 3
        assert fb3["raw_evidence"] == "3 downstream outputs"
        assert fb3["factor_score"] == 85.0
        assert fb3["weighted_contribution_pct"] == 17.0
        assert res3.score > res1.score

        # 0 outputs
        res0 = calculate_workflow_criticality(
            workflow_id="wf_dyn_out_0",
            workflow_filename="DynOut0.yxmd",
            sources=["input.csv"],
            targets=[],
        )
        fb0 = res0.factor_breakdown["downstream_outputs"]
        assert fb0["raw_value"] == 0
        assert fb0["raw_evidence"] == "0 downstream outputs"
        assert fb0["factor_score"] == 0.0
        assert fb0["weighted_contribution_pct"] == 0.0

    def test_dynamic_upstream_sources_evidence_variation(self):
        """Changing upstream sources changes the calculated count, value, score, and contribution."""
        # 1 source
        res1 = calculate_workflow_criticality(
            workflow_id="wf_dyn_src_1",
            workflow_filename="DynSrc1.yxmd",
            sources=["Customers.csv"],
            targets=["out.yxdb"],
        )
        fb1 = res1.factor_breakdown["upstream_sources"]
        assert fb1["raw_value"] == 1
        assert fb1["raw_evidence"] == "1 upstream source"
        assert fb1["factor_score"] == 40.0
        assert fb1["weighted_contribution_pct"] == 8.0

        # 4 sources
        sources_4 = ["Customers.csv", "Orders.xlsx", "Products.db", "Returns.csv"]
        res4 = calculate_workflow_criticality(
            workflow_id="wf_dyn_src_4",
            workflow_filename="DynSrc4.yxmd",
            sources=sources_4,
            targets=["out.yxdb"],
        )
        fb4 = res4.factor_breakdown["upstream_sources"]
        assert fb4["raw_value"] == 4
        assert fb4["raw_evidence"] == "4 upstream sources"
        assert fb4["factor_score"] == 90.0
        assert fb4["weighted_contribution_pct"] == 18.0
        assert res4.score > res1.score

        # 0 sources
        res0 = calculate_workflow_criticality(
            workflow_id="wf_dyn_src_0",
            workflow_filename="DynSrc0.yxmd",
            sources=[],
            targets=["out.yxdb"],
        )
        fb0 = res0.factor_breakdown["upstream_sources"]
        assert fb0["raw_value"] == 0
        assert fb0["raw_evidence"] == "0 upstream sources"
        assert fb0["factor_score"] == 0.0
        assert fb0["weighted_contribution_pct"] == 0.0

    def test_dynamic_etl_consumers_evidence_variation(self):
        """Changing portfolio consumers dynamically updates the consumer factor score and contribution."""
        # 0 consumers
        ctx0 = PortfolioDependencyContext()
        res0 = calculate_workflow_criticality(
            workflow_id="wf_c0",
            workflow_filename="C0.yxmd",
            sources=["s.csv"],
            targets=["t.yxdb"],
            context=ctx0,
        )
        assert res0.factor_breakdown["etl_consumers"]["raw_value"] == 0
        assert res0.factor_breakdown["etl_consumers"]["raw_evidence"] == "0 consuming ETL workflows"
        assert res0.factor_breakdown["etl_consumers"]["factor_score"] == 0.0
        assert res0.factor_breakdown["etl_consumers"]["weighted_contribution_pct"] == 0.0

        # 2 consumers
        ctx2 = PortfolioDependencyContext(
            source_to_consumers={
                "t.yxdb": [("wf_c1", "Consumer_Pipeline.yxmd"), ("wf_c2", "Executive_Dashboard.yxmd")],
            }
        )
        res2 = calculate_workflow_criticality(
            workflow_id="wf_c0",
            workflow_filename="C0.yxmd",
            sources=["s.csv"],
            targets=["t.yxdb"],
            context=ctx2,
        )
        fb2 = res2.factor_breakdown["etl_consumers"]
        assert fb2["raw_value"] == 2
        assert fb2["raw_evidence"] == "2 consuming ETL workflows"
        assert fb2["factor_score"] == 80.0
        assert fb2["weighted_contribution_pct"] == 16.0
        assert res2.score > res0.score

    def test_dynamic_operational_metadata_evidence_variation(self):
        """Changing operational metadata dynamically calculates last_run and frequency evidence."""
        # Missing metadata
        res_none = calculate_workflow_criticality(
            workflow_id="wf_op_none",
            workflow_filename="OpNone.yxmd",
            sources=["s.csv"],
            targets=["t.yxdb"],
            operational_metadata=None,
        )
        assert res_none.factor_breakdown["last_run"]["raw_evidence"] == "Not documented"
        assert res_none.factor_breakdown["last_run"]["factor_score"] == 0.0
        assert res_none.factor_breakdown["frequency"]["raw_evidence"] == "Not documented"
        assert res_none.factor_breakdown["frequency"]["factor_score"] == 0.0

        # Real metadata: 3 days ago / Daily
        res_real = calculate_workflow_criticality(
            workflow_id="wf_op_real",
            workflow_filename="OpReal.yxmd",
            sources=["s.csv"],
            targets=["t.yxdb"],
            operational_metadata={"last_run": "3 days ago", "frequency": "Daily"},
        )
        assert res_real.factor_breakdown["last_run"]["raw_evidence"] == "3 days ago"
        assert res_real.factor_breakdown["last_run"]["factor_score"] == 100.0
        assert res_real.factor_breakdown["last_run"]["weighted_contribution_pct"] == 20.0
        assert res_real.factor_breakdown["frequency"]["raw_evidence"] == "Daily"
        assert res_real.factor_breakdown["frequency"]["factor_score"] == 90.0
        assert res_real.factor_breakdown["frequency"]["weighted_contribution_pct"] == 18.0

    def test_weighted_contributions_sum_to_final_score(self):
        """Sum of all 5 weighted contributions must equal the final criticality score."""
        res = calculate_workflow_criticality(
            workflow_id="wf_sum_check",
            workflow_filename="SumCheck.yxmd",
            sources=["s1.csv", "s2.xlsx"],
            targets=["t1.yxdb"],
            operational_metadata={"last_run": "2 weeks ago", "frequency": "Weekly"},
        )
        sum_contribs = sum(item["weighted_contribution_pct"] for item in res.factor_breakdown.values())
        assert abs(sum_contribs - res.score) < 0.15

    def test_real_yxmd_parsing_drives_deterministic_criticality(self):
        """Authoritative YXMD parser extracts real sources and targets which populate criticality."""
        from awa.analysis.workflow_analyzer import analyze_canonical

        res = analyze_canonical("fixtures/joins/join_workflow.yxmd")

        assert res.business_summary is not None
        assert res.business_summary.criticality_source == "deterministic"
        assert res.business_summary.criticality_score is not None
        assert res.business_summary.criticality_score > 0.0
        assert len(res.business_summary.criticality_factors) == 5

        # Check factor breakdown has real sources/targets
        fb = res.business_summary.factor_assessments
        assert fb["downstream_outputs"]["name"] == "Downstream outputs"
        assert fb["upstream_sources"]["name"] == "Upstream sources"
        assert fb["etl_consumers"]["name"] == "ETL workflow consumers"
        assert fb["last_run"]["name"] == "Last Run"
        assert fb["frequency"]["name"] == "Frequency"


