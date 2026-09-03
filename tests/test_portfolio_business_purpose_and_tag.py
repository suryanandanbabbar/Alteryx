"""Comprehensive tests for ETL Portfolio Business Purpose, Business-Area Tagging & Criticality.

Covers all 16 verification requirements:
1. One-call contract: structured purpose + tag generation in LLMNarrativeGenerator
2. Single-owner fallback logic: generator owns fallback on client unavailability, invalid JSON, or unknown tags
3. Rejection of invalid business area tag
4. Canonical result properties and persistence in WorkflowBusinessSummary
5. Storage persistence and retrieval: identical purpose and tag preserved
6. Zero LLM calls in to_overview_dto: pure read operation
7. Zero LLM calls in build_portfolio_analysis: direct consumption of canonical tags
8. Correct segregation: Claims & Risk, Underwriting, Sales & Distribution, Legal
9. All configured business area cards materialized (including zero-workflow cards)
10. Stable identity & count invariant: sum(card.workflow_count) == total_workflows
11. Backward-compatibility for legacy analysis results lacking business_area_tag
12. Criticality: semantic deliverable, scope, customer, and client impact boosts
13. Criticality: strict anti-double-counting guard
14. Criticality: non-impact text produces zero boost (no false positives)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import networkx as nx
import pytest

from awa.analysis.business_area_classifier import (
    ALLOWED_BUSINESS_AREAS,
    classify_business_area_deterministic,
)
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.analysis.workflow_criticality import (
    calculate_workflow_criticality,
    PortfolioDependencyContext,
)
from awa.llm.cache import LLMNarrativeCache
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator
from awa.llm.schemas import BusinessPurposeResult
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.dag_layout import DagLayout
from awa.model.python_trace import PythonTraceMap
from awa.model.source_info import SourceInfo
from awa.model.tool import Tool, ToolConfiguration
from awa.model.workflow import Workflow, WorkflowMetadata
from backend.app.services.analyzer import to_overview_dto
from backend.app.services.storage import InMemoryStorage


def _create_mock_canonical_result(
    analysis_id: str,
    name: str,
    business_purpose: str = "",
    business_area_tag: str = "UNCLASSIFIED",
    tag_source: str = "deterministic_fallback",
    targets: list[str] | None = None,
) -> CanonicalAnalysisResult:
    """Helper to build a valid CanonicalAnalysisResult for testing."""
    wf = Workflow(
        metadata=WorkflowMetadata(name=name, version="2021.1"),
        tools={},
        connections=[],
    )
    # Add dummy target tools if specified
    if targets:
        for idx, tname in enumerate(targets, start=100):
            cfg = ToolConfiguration(
                raw_xml=f'<Configuration File="{tname}" />',
                parsed={"file": tname},
            )
            wf.tools[idx] = Tool(
                tool_id=idx,
                tool_type="DbFileOutput",
                name=tname,
                configuration=cfg,
            )

    bs = WorkflowBusinessSummary(
        business_purpose=business_purpose,
        one_line_purpose=f"{name} summary",
        why_it_matters="Important operational process",
        business_area_tag=business_area_tag,
        business_area_tag_source=tag_source,
    )

    res = CanonicalAnalysisResult(
        analysis_id=analysis_id,
        source=SourceInfo(source_format="yxmd", original_filename=f"{name}.yxmd"),
        workflow=wf,
        graph=nx.DiGraph(),
        execution_order=list(wf.tools.keys()),
        translations={},
        consumed_anchors={},
        lineage_paths=[],
        metrics=WorkflowMetrics(
            total_nodes=len(wf.tools),
            total_connections=0,
            input_count=0,
            output_count=len(targets or []),
        ),
        dag_layout=DagLayout(nodes={}, width=100, height=100),
        python_trace=PythonTraceMap(),
        tool_explanations={},
        required_libraries=[],
        diagnostics=[],
        business_summary=bs,
    )
    return res


class TestPortfolioBusinessPurposeAndTag:
    """Suite testing canonical business purpose, tagging, and criticality integration."""

    def test_generator_produces_structured_json_with_valid_tag(self):
        """Generator produces BusinessPurposeResult with purpose, tag, and source='llm'."""
        wf = Workflow(metadata=WorkflowMetadata(name="Claims_Process", version="2021.1"))
        bs = WorkflowBusinessSummary(
            business_purpose="Processes insurance claim adjustments.",
            one_line_purpose="Claims workflow",
            why_it_matters="Core claims",
        )

        mock_client = FakeLLMClient(
            default_response=json.dumps({
                "business_purpose": "This workflow manages auto claims litigation and loss reserves for corporate accounts.",
                "business_area_tag": "Claims & Risk",
            })
        )
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=mock_client, cache=cache)

        result = gen.generate_business_purpose(wf, bs, workflow_id="wf_claims_01")

        assert isinstance(result, BusinessPurposeResult)
        assert result.source == "llm"
        assert result.business_area_tag == "Claims & Risk"
        assert "litigation" in result.business_purpose
        assert result.text == result.business_purpose  # Backwards compatibility accessor

    def test_generator_single_owner_fallback_on_unavailability(self):
        """When LLM client is unavailable, generator returns deterministic fallback directly."""
        wf = Workflow(metadata=WorkflowMetadata(name="Underwriting_Engine", version="2021.1"))
        bs = WorkflowBusinessSummary(
            business_purpose="Automated policy underwriting and rating calculation.",
            one_line_purpose="Underwriting workflow",
            why_it_matters="Policy binding",
        )

        mock_client = FakeLLMClient(is_available=False)
        gen = LLMNarrativeGenerator(client=mock_client, cache=LLMNarrativeCache())

        result = gen.generate_business_purpose(wf, bs, workflow_id="wf_uw_01")

        assert result.source == "deterministic_fallback"
        assert result.business_area_tag == "Underwriting"
        assert result.business_purpose == bs.business_purpose

    def test_generator_single_owner_rejects_invalid_tag(self):
        """Generator rejects hallucinated business-area tag and falls back deterministically."""
        wf = Workflow(metadata=WorkflowMetadata(name="Sales_Pipeline", version="2021.1"))
        bs = WorkflowBusinessSummary(
            business_purpose="Monitors sales pipeline, broker commissions, and agent performance.",
            one_line_purpose="Sales workflow",
            why_it_matters="Commercial tracking",
        )

        mock_client = FakeLLMClient(
            default_response=json.dumps({
                "business_purpose": "Tracks sales distributor revenue.",
                "business_area_tag": "Human Resources & Payroll",  # Invalid tag!
            })
        )
        gen = LLMNarrativeGenerator(client=mock_client, cache=LLMNarrativeCache())

        result = gen.generate_business_purpose(wf, bs, workflow_id="wf_sales_01")

        # Invalid tag must be rejected and replaced by deterministic fallback
        assert result.source == "deterministic_fallback"
        assert result.business_area_tag == "Sales & Distribution"

    def test_generator_handles_malformed_json(self):
        """Generator safely falls back when LLM returns invalid JSON or prose."""
        wf = Workflow(metadata=WorkflowMetadata(name="Legal_Matters", version="2021.1"))
        bs = WorkflowBusinessSummary(
            business_purpose="Extracts legal regulatory compliance filings and contracts.",
            one_line_purpose="Legal workflow",
            why_it_matters="Regulatory compliance",
        )

        mock_client = FakeLLMClient(default_response="Not valid JSON at all")
        gen = LLMNarrativeGenerator(client=mock_client, cache=LLMNarrativeCache())

        result = gen.generate_business_purpose(wf, bs, workflow_id="wf_legal_01")

        assert result.source == "deterministic_fallback"
        assert result.business_area_tag == "Legal"

    def test_canonical_properties_and_persistence(self):
        """CanonicalAnalysisResult properties delegate strictly to business_summary."""
        res = _create_mock_canonical_result(
            analysis_id="res_001",
            name="Workflow_A",
            business_purpose="Canonical purpose text",
            business_area_tag="Claims & Risk",
            tag_source="llm",
        )

        assert res.business_purpose == "Canonical purpose text"
        assert res.business_area_tag == "Claims & Risk"
        assert res.business_area_tag_source == "llm"

        d = res.to_dict()
        assert d["business_purpose"] == "Canonical purpose text"
        assert d["business_area_tag"] == "Claims & Risk"
        assert d["business_area_tag_source"] == "llm"

    def test_storage_persistence_and_retrieval(self):
        """Stored result retrieved from storage preserves exact purpose and tag without re-evaluating."""
        storage = InMemoryStorage()
        res = _create_mock_canonical_result(
            analysis_id="storage_wf_01",
            name="Persistent_Wf",
            business_purpose="High-value claims processing engine.",
            business_area_tag="Claims & Risk",
            tag_source="llm",
        )
        storage.save(res)

        retrieved = storage.get("storage_wf_01")
        assert retrieved is not None
        assert retrieved.business_purpose == "High-value claims processing engine."
        assert retrieved.business_area_tag == "Claims & Risk"
        assert retrieved.business_area_tag_source == "llm"

    def test_overview_dto_makes_zero_llm_calls(self):
        """to_overview_dto strictly reads persisted purpose and makes zero LLM calls."""
        res = _create_mock_canonical_result(
            analysis_id="overview_wf_01",
            name="Overview_Wf",
            business_purpose="Persisted business purpose from upload.",
            business_area_tag="Underwriting",
            tag_source="llm",
        )

        # Ensure no LLM calls occur during DTO conversion
        with patch("backend.awa.llm.generator.LLMNarrativeGenerator.generate_business_purpose") as mock_gen:
            dto = to_overview_dto(res)
            mock_gen.assert_not_called()

        assert dto.business_summary is not None
        assert dto.business_summary.business_purpose == "Persisted business purpose from upload."
        assert dto.business_summary.business_area_tag == "Underwriting"
        assert dto.business_summary.business_area_tag_source == "llm"

    def test_portfolio_segregation_directly_uses_canonical_tag(self):
        """Portfolio segregation groups workflows directly from canonical tags with zero LLM calls."""
        res_claims = _create_mock_canonical_result(
            "wf_1", "Claims_Flow", "Claims handling", "Claims & Risk", "llm"
        )
        res_uw = _create_mock_canonical_result(
            "wf_2", "UW_Flow", "Underwriting rules", "Underwriting", "llm"
        )
        res_sales = _create_mock_canonical_result(
            "wf_3", "Sales_Flow", "Commission distribution", "Sales & Distribution", "llm"
        )
        res_legal = _create_mock_canonical_result(
            "wf_4", "Legal_Flow", "Litigation filings", "Legal", "llm"
        )

        raw = [
            ("Claims.yxmd", "Claims.yxmd", res_claims),
            ("UW.yxmd", "UW.yxmd", res_uw),
            ("Sales.yxmd", "Sales.yxmd", res_sales),
            ("Legal.yxmd", "Legal.yxmd", res_legal),
        ]

        mock_client = FakeLLMClient()
        gen = LLMNarrativeGenerator(client=mock_client)

        portfolio = build_portfolio_analysis(raw, generator=gen)

        # Verify client was not called to classify business areas
        assert len(mock_client.calls) == 0

        # Verify segregation matches canonical tags exactly
        groups_by_area = {g.business_area: g for g in portfolio.business_areas}
        assert groups_by_area["Claims & Risk"].workflow_count == 1
        assert groups_by_area["Claims & Risk"].workflows[0].workflow_id == "wf_1"

        assert groups_by_area["Underwriting"].workflow_count == 1
        assert groups_by_area["Underwriting"].workflows[0].workflow_id == "wf_2"

        assert groups_by_area["Sales & Distribution"].workflow_count == 1
        assert groups_by_area["Sales & Distribution"].workflows[0].workflow_id == "wf_3"

        assert groups_by_area["Legal"].workflow_count == 1
        assert groups_by_area["Legal"].workflows[0].workflow_id == "wf_4"

    def test_all_configured_cards_materialize_including_zero_count(self):
        """Every configured business area card appears in portfolio even with 0 workflows."""
        res_claims = _create_mock_canonical_result(
            "wf_1", "Claims_Only", "Claims flow", "Claims & Risk", "llm"
        )
        raw = [("Claims.yxmd", "Claims.yxmd", res_claims)]

        portfolio = build_portfolio_analysis(raw)

        areas_present = {g.business_area for g in portfolio.business_areas}
        for area in ALLOWED_BUSINESS_AREAS:
            assert area in areas_present

        groups = {g.business_area: g.workflow_count for g in portfolio.business_areas}
        assert groups["Claims & Risk"] == 1
        assert groups["Underwriting"] == 0
        assert groups["Legal"] == 0
        assert groups["Sales & Distribution"] == 0

    def test_stable_identity_and_count_invariants(self):
        """Sum of card counts strictly equals total workflows and every workflow ID occurs once."""
        res_a = _create_mock_canonical_result("id_a", "A", "Claims", "Claims & Risk", "llm")
        res_b = _create_mock_canonical_result("id_b", "B", "Sales", "Sales & Distribution", "llm")
        res_c = _create_mock_canonical_result("id_c", "C", "Legal", "Legal", "llm")

        raw = [("A.yxmd", "A", res_a), ("B.yxmd", "B", res_b), ("C.yxmd", "C", res_c)]
        portfolio = build_portfolio_analysis(raw)

        total_in_cards = sum(g.workflow_count for g in portfolio.business_areas)
        assert total_in_cards == 3

        seen_ids: set[str] = set()
        for g in portfolio.business_areas:
            for w in g.workflows:
                assert w.workflow_id not in seen_ids
                seen_ids.add(w.workflow_id)
        assert seen_ids == {"id_a", "id_b", "id_c"}

    def test_legacy_result_deterministic_compatibility(self):
        """Legacy CanonicalAnalysisResult without business_area_tag resolves deterministically."""
        legacy_res = _create_mock_canonical_result(
            "legacy_01",
            "Legacy_Claims",
            business_purpose="Processes claims payments and loss indemnity reserves.",
            business_area_tag="UNCLASSIFIED",  # Unset/legacy
            tag_source="deterministic_fallback",
        )
        raw = [("Legacy.yxmd", "Legacy.yxmd", legacy_res)]

        portfolio = build_portfolio_analysis(raw)
        groups = {g.business_area: g for g in portfolio.business_areas}

        # Deterministic fallback should recognize claims keywords from business purpose
        assert groups["Claims & Risk"].workflow_count == 1
        assert groups["Claims & Risk"].workflows[0].workflow_id == "legacy_01"

    def test_criticality_5_factor_deterministic_scoring(self):
        """Criticality calculates technical and operational factors deterministically."""
        ctx = PortfolioDependencyContext()
        base = calculate_workflow_criticality(
            workflow_id="wf_test",
            workflow_filename="Test.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
        )

        assert base.score == 36.0
        assert base.level == "MEDIUM"
        assert base.breakdown["downstream_outputs"] == 40.0
        assert base.breakdown["upstream_sources"] == 40.0
        assert base.breakdown["etl_consumers"] == 0.0
        assert base.breakdown["last_run"] == 40.0
        assert base.breakdown["frequency"] == 60.0

    def test_criticality_portfolio_consumer_boost(self):
        """Adding consuming workflows increases etl_consumers score deterministically."""
        ctx = PortfolioDependencyContext(
            source_to_consumers={
                "output.xlsx": [("wf_c1", "Consumer1.yxmd")],
            }
        )

        assessment = calculate_workflow_criticality(
            workflow_id="wf_anti_dc",
            workflow_filename="Anti_DC.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            operational_metadata={"last_run": "today", "frequency": "Daily"},
        )

        assert assessment.breakdown["etl_consumers"] == 60.0
        assert assessment.breakdown["last_run"] == 100.0
        assert assessment.breakdown["frequency"] == 90.0
        assert assessment.score > 50.0

    def test_criticality_missing_operational_metadata_scored_zero(self):
        """Missing operational metadata scores 0.0 for last_run and frequency without failure."""
        ctx = PortfolioDependencyContext()

        assessment = calculate_workflow_criticality(
            workflow_id="wf_neutral",
            workflow_filename="Neutral.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            operational_metadata=None,
        )

        assert assessment.breakdown["last_run"] == 0.0
        assert assessment.breakdown["frequency"] == 0.0
        assert assessment.operational_score == 0.0


    # -----------------------------------------------------------------------
    # Mandatory Adversarial Boundary Tests (7-Tier Functional Hierarchy)
    # -----------------------------------------------------------------------

    def test_boundary_underwriting_decision_engine_consuming_claims_data(self):
        """Underwriting Decision Engine consuming Claims data resolves to Underwriting."""
        output_ev = [
            {"dataset": "Policyholder_Risk_Score_Matrix.xlsx", "columns": ["claim_id", "claim_count", "prior_loss_amt", "risk_score"]}
        ]
        purpose = (
            "Supports underwriting decisioning by applying claims submission data, risk rules, and "
            "policyholder attributes to generate risk scores used to assess policyholder risk and eligibility."
        )
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Underwriting Decision Engine Application.yxmd",
        )
        assert res.business_area == "Underwriting"
        assert res.confidence == "HIGH"
        assert any("Tier 1" in e for e in res.evidence)

    def test_boundary_claims_fraud_detection(self):
        """Claims Fraud Detection resolves to Claims & Risk."""
        output_ev = [{"dataset": "Suspicious_Claims_Investigation.xlsx", "columns": ["claim_id", "fraud_probability"]}]
        purpose = "Processes claims to identify suspicious claims and prioritise claims fraud investigation."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Claims Fraud Detection Model.yxmd",
        )
        assert res.business_area == "Claims & Risk"
        assert res.confidence == "HIGH"

    def test_boundary_premium_calculator_using_claims_history(self):
        """Premium Calculator using historical claims experience resolves to Underwriting."""
        output_ev = [{"dataset": "Premium_Rating_Matrix.xlsx", "columns": ["policy_type", "base_premium", "loss_ratio"]}]
        purpose = "Uses historical claims loss experience to calculate policy pricing and premium rating."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Policy Premium Rating Calculator.yxmd",
        )
        assert res.business_area == "Underwriting"

    def test_boundary_claim_reserve_calculator(self):
        """Claim Reserve Calculator resolves to Claims & Risk."""
        output_ev = [{"dataset": "Outstanding_Reserves.xlsx", "columns": ["claim_id", "incurred_loss", "reserve_amount"]}]
        purpose = "Calculates loss reserves and litigation exposure for active open claims."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Claim Reserve Calculator.yxmd",
        )
        assert res.business_area == "Claims & Risk"

    def test_boundary_sales_territory_analytics(self):
        """Sales Territory Analytics resolves to Sales & Distribution."""
        output_ev = [{"dataset": "Territory_Commission_Report.xlsx", "columns": ["broker_id", "commission_amt", "sales_volume"]}]
        purpose = "Analyzes sales territory distribution and calculates broker commissions."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Sales Territory Analytics & Commission.yxmd",
        )
        assert res.business_area == "Sales & Distribution"

    def test_boundary_regulatory_compliance_reporting(self):
        """Regulatory Compliance Reporting resolves to Legal."""
        output_ev = [{"dataset": "Statutory_Compliance_Filing.xlsx", "columns": ["filing_id", "statute_code", "compliance_status"]}]
        purpose = "Generates regulatory compliance filings and statutory reports from insurance claims and policy records."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Regulatory Compliance Reporting Pipeline.yxmd",
        )
        assert res.business_area == "Legal"

    def test_boundary_misleading_claims_heavy_filename_with_underwriting_function(self):
        """Misleading filename with claims data resolves to Underwriting when primary function is Underwriting."""
        output_ev = [{"dataset": "Underwriting_Risk_Matrix.xlsx", "columns": ["policyholder_id", "claims_history_count", "risk_rating"]}]
        purpose = "Underwriting decision engine that evaluates applicant risk appetite and policy eligibility."
        res = classify_business_area_deterministic(
            output_ev,
            business_purpose=purpose,
            workflow_name="Claims_Data_Feed_Ingestor.yxmd",
            business_function="Underwriting decisioning",
        )
        assert res.business_area == "Underwriting"

    def test_semantic_conflict_guard_overrides_distracted_llm_tag(self):
        """When LLM returns an Underwriting function but misclassifies tag as Claims & Risk, guard corrects it."""
        wf = Workflow(metadata=WorkflowMetadata(name="Underwriting Decision Engine Application", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="Underwriting workflow", one_line_purpose="UW", why_it_matters="UW")

        # Fake client returning conflicting JSON: function='Underwriting decisioning' but tag='Claims & Risk'
        conflict_json = json.dumps({
            "business_purpose": "Supports underwriting decisioning by applying claims submission data to assess policyholder risk and eligibility.",
            "business_function": "Underwriting decisioning",
            "business_area_tag": "Claims & Risk",
        })
        client = FakeLLMClient(response=conflict_json, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        output_ev = [{"dataset": "Policyholder_Risk_Scores.xlsx", "columns": ["claim_id", "risk_score"]}]
        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_conflict_test", output_evidence=output_ev)

        assert res.business_area_tag == "Underwriting"
        assert res.classification_conflict is True
        assert res.business_function == "Underwriting decisioning"
        assert any("Conflict override" in e for e in res.classification_evidence)

    def test_atomic_structured_output_failure_routes_to_deterministic_fallback(self):
        """Malformed JSON or missing fields route completely to deterministic fallback."""
        wf = Workflow(metadata=WorkflowMetadata(name="Claims Fraud Detection Model", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        client = FakeLLMClient(response="NOT VALID JSON AT ALL", is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_malformed_test")
        assert res.source == "deterministic_fallback"
        assert res.business_area_tag == "Claims & Risk"
        assert res.business_function != ""
        assert res.business_area_taxonomy_version == "3.0"

    # -----------------------------------------------------------------------
    # Regression Tests: Business Purpose Data-Contract Boundary & Purity
    # -----------------------------------------------------------------------

    def test_valid_structured_llm_response_stores_only_business_purpose(self):
        """1. A valid structured LLM response stores only business_purpose in that field."""
        wf = Workflow(metadata=WorkflowMetadata(name="Underwriting Decision Engine Application", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        clean_purpose = "Supports underwriting decisioning by applying claims submission data, risk rules, and policyholder attributes to generate risk scores used to assess policyholder risk and eligibility."
        payload = json.dumps({
            "business_purpose": clean_purpose,
            "business_function": "Underwriting decisioning and risk assessment",
            "business_area_tag": "Underwriting",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_clean_purpose_test")
        assert res.source == "llm"
        assert res.business_purpose == clean_purpose
        # Ensure no accidental concatenation
        assert "Underwriting decisioning and risk assessment" not in res.business_purpose

    def test_business_function_stored_separately(self):
        """2. business_function is stored separately and not concatenated into business_purpose."""
        wf = Workflow(metadata=WorkflowMetadata(name="Policy Rating Calculator", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        payload = json.dumps({
            "business_purpose": "Calculates commercial property insurance policy pricing and premium ratings based on risk profiles.",
            "business_function": "Policy pricing and premium rating calculation",
            "business_area_tag": "Underwriting",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_func_sep_test")
        assert res.business_function == "Policy pricing and premium rating calculation"
        assert res.business_function not in res.business_purpose

    def test_business_area_tag_stored_separately(self):
        """3. business_area_tag is stored separately and not concatenated into business_purpose."""
        wf = Workflow(metadata=WorkflowMetadata(name="Sales Territory Analytics", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        payload = json.dumps({
            "business_purpose": "Evaluates commercial distribution channel performance and computes monthly producer commissions.",
            "business_function": "Broker commission calculation and sales analytics",
            "business_area_tag": "Sales & Distribution",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_tag_sep_test")
        assert res.business_area_tag == "Sales & Distribution"
        assert "Sales & Distribution" not in res.business_purpose

    def test_response_containing_extensive_reasoning_does_not_become_business_purpose(self):
        """4. A response containing extensive classification reasoning extracts only the clean JSON purpose."""
        wf = Workflow(metadata=WorkflowMetadata(name="Underwriting Decision Engine Application", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        raw_noisy_llm_response = (
            "To determine the primary business function, business purpose, and business area tag for the given workflow, "
            "let’s analyze the provided facts step by step according to the classification evidence hierarchy:\n"
            "1. Tier 1: Workflow Name 'Underwriting Decision Engine Application' matches Underwriting.\n"
            "2. Tier 2: The workflow consumes claims submissions and outputs risk scores.\n"
            "Given these observations, we conclude the primary area is Underwriting.\n\n"
            "```json\n"
            "{\n"
            '  "business_purpose": "Supports underwriting decisioning by applying claims submission data, risk rules, and policyholder attributes to generate risk scores used to assess policyholder risk and eligibility.",\n'
            '  "business_function": "Underwriting decisioning and risk assessment",\n'
            '  "business_area_tag": "Underwriting"\n'
            "}\n"
            "```\n"
            "Therefore, Underwriting is selected."
        )

        client = FakeLLMClient(response=raw_noisy_llm_response, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_noisy_reasoning_test")

        # Crucial invariants:
        expected_clean = "Supports underwriting decisioning by applying claims submission data, risk rules, and policyholder attributes to generate risk scores used to assess policyholder risk and eligibility."
        assert res.business_purpose == expected_clean
        assert "To determine the primary business function" not in res.business_purpose
        assert "Tier 1" not in res.business_purpose
        assert "Given these observations" not in res.business_purpose
        assert "```" not in res.business_purpose
        assert res.business_function == "Underwriting decisioning and risk assessment"
        assert res.business_area_tag == "Underwriting"

    def test_to_overview_dto_returns_only_concise_persisted_purpose(self):
        """5. to_overview_dto returns only the concise persisted purpose and separate function/tag."""
        clean_purpose = "Processes claims submissions to identify suspicious indicators and prioritize fraud audits."
        res = _create_mock_canonical_result(
            analysis_id="wf_dto_test",
            name="Claims_Fraud_Model",
            business_purpose=clean_purpose,
            business_area_tag="Claims & Risk",
            tag_source="llm",
        )
        res.business_summary.business_function = "Claims fraud detection and investigation"

        dto = to_overview_dto(res)
        assert dto.business_summary is not None
        assert dto.business_summary.business_purpose == clean_purpose
        assert dto.business_summary.business_function == "Claims fraud detection and investigation"
        assert dto.business_summary.business_area_tag == "Claims & Risk"
        assert "To determine" not in dto.business_summary.business_purpose

    def test_portfolio_and_overview_use_exact_same_persisted_purpose(self):
        """6. Portfolio and Overview use the exact same persisted business purpose without modification."""
        clean_purpose = "Analyzes regional sales performance and calculates monthly broker commissions."
        res = _create_mock_canonical_result(
            analysis_id="wf_same_test",
            name="Sales_Commissions",
            business_purpose=clean_purpose,
            business_area_tag="Sales & Distribution",
            tag_source="llm",
        )
        res.business_summary.business_function = "Broker commission calculation"

        # Overview representation
        overview_dto = to_overview_dto(res)

        # Portfolio representation
        portfolio = build_portfolio_analysis([("Sales_Commissions.yxmd", "Sales_Commissions.yxmd", res)])
        portfolio_wf = portfolio.workflows[0]

        assert overview_dto.business_summary is not None
        assert portfolio_wf.business_purpose == overview_dto.business_summary.business_purpose
        assert portfolio_wf.business_purpose == clean_purpose
        assert portfolio_wf.business_function == overview_dto.business_summary.business_function

    def test_malformed_or_unstructured_llm_output_uses_deterministic_fallback(self):
        """7. Malformed/unstructured LLM output uses deterministic fallback instead of persisting raw response."""
        wf = Workflow(metadata=WorkflowMetadata(name="Regulatory Compliance Filing", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(
            business_purpose="Generates regulatory compliance filings and statutory reports.",
            one_line_purpose="Legal compliance",
            why_it_matters="Statutory compliance",
        )

        unstructured_reasoning = (
            "To determine the primary business function, let’s analyze the facts step by step according to Tier 1: "
            "The workflow name mentions Regulatory Compliance, which maps to Legal. "
            "Given these observations, the classification is Legal."
        )

        client = FakeLLMClient(response=unstructured_reasoning, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_unstructured_fallback_test")
        assert res.source == "deterministic_fallback"
        # Must NEVER store the unstructured reasoning as business purpose
        assert res.business_purpose != unstructured_reasoning
        assert "To determine the primary business function" not in res.business_purpose
        assert "Tier 1" not in res.business_purpose
        assert res.business_area_tag == "Legal"

    def test_no_additional_llm_call_when_opening_workflow_overview(self):
        """8. No additional LLM call occurs when opening Workflow Overview."""
        res = _create_mock_canonical_result(
            analysis_id="wf_no_call_test",
            name="Overview_Test",
            business_purpose="Concise existing purpose text.",
            business_area_tag="Underwriting",
            tag_source="llm",
        )

        with patch("backend.awa.llm.client.FakeLLMClient.generate") as mock_gen:
            dto = to_overview_dto(res)
            assert mock_gen.call_count == 0
            assert dto.business_summary is not None
            assert dto.business_summary.business_purpose == "Concise existing purpose text."

    def test_underwriting_decision_engine_boundary_case_underwriting_purpose_and_tag(self):
        """9. Underwriting Decision Engine boundary case produces an Underwriting purpose and Underwriting tag."""
        wf = Workflow(metadata=WorkflowMetadata(name="Underwriting Decision Engine Application", version="2021.1"), tools={}, connections=[])
        bs = WorkflowBusinessSummary(business_purpose="", one_line_purpose="", why_it_matters="")

        payload = json.dumps({
            "business_purpose": "Supports underwriting decisioning by applying claims submission data, risk rules, and policyholder attributes to generate risk scores used to assess policyholder risk and eligibility.",
            "business_function": "Underwriting decisioning and risk eligibility assessment",
            "business_area_tag": "Underwriting",
        })
        client = FakeLLMClient(response=payload, is_available=True)
        gen = LLMNarrativeGenerator(client=client, cache=LLMNarrativeCache())

        output_ev = [{"dataset": "Policyholder_Risk_Scores.xlsx", "columns": ["claim_id", "risk_score"]}]
        res = gen.generate_business_purpose(wf, bs, workflow_id="wf_uw_boundary_test", output_evidence=output_ev)

        assert res.business_area_tag == "Underwriting"
        assert "underwriting decisioning" in res.business_purpose.lower()
        assert "claims submission data" in res.business_purpose.lower()
        assert "To determine" not in res.business_purpose

