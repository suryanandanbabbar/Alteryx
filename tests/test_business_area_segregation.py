"""Comprehensive tests for Business-Area Workflow Segregation in ETL Rationalisation.

Covers all 10 requirements from prompt Section 19:
Case 1 — All business areas populated
Case 2 — Some business areas empty (0 workflows cards rendered)
Case 3 — All business areas empty (zero workflows estate)
Case 4 — LLM successfully classifies (business purpose included in LLM input)
Case 5 — LLM fails (deterministic fallback used, every workflow receives valid classification)
Case 6 — Partial LLM response (unreturned workflows resolved via fallback)
Case 7 — Invalid business area (rejected, fallback used, no invalid cards)
Case 8 — Unknown workflow ID (rejected, no phantom workflows created)
Case 9 — Business-purpose-driven classification
Case 10 — Count invariant (sum of counts == total workflows, every workflow occurs once)
"""

import json
from unittest.mock import MagicMock

import pytest

from awa.analysis.business_area_classifier import (
    ALLOWED_BUSINESS_AREAS,
    classify_business_area_deterministic,
    classify_portfolio_business_areas,
    classify_workflow_business_area,
)
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.llm.cache import LLMNarrativeCache
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.tool import Tool, ToolConfiguration


def _make_dummy_canonical_result(
    analysis_id: str,
    filename: str,
    business_purpose: str = "",
    target_files: list[str] | None = None,
    output_columns: list[str] | None = None,
) -> CanonicalAnalysisResult:
    """Create a lightweight CanonicalAnalysisResult with business summary and target tools."""
    res = MagicMock(spec=CanonicalAnalysisResult)
    res.analysis_id = analysis_id

    # Source info
    res.source = MagicMock()
    res.source.original_filename = filename

    # Metadata
    res.workflow = MagicMock()
    res.workflow.metadata = MagicMock()
    res.workflow.metadata.name = filename
    res.workflow.connections = []

    # Execution order & tools
    res.execution_order = []
    res.workflow.tools = {}
    res.graph = MagicMock()
    res.graph.has_node = MagicMock(return_value=True)
    res.graph.out_degree = MagicMock(return_value=0)
    res.graph.predecessors = MagicMock(return_value=[])
    res.graph.number_of_nodes = MagicMock(return_value=1)
    res.graph.number_of_edges = MagicMock(return_value=0)
    res.graph.nodes = ["1"]
    res.graph.edges = []

    target_files = target_files or []
    output_columns = output_columns or []

    for idx, tgt in enumerate(target_files, 1):
        tid = str(idx)
        res.execution_order.append(tid)
        tool = MagicMock(spec=Tool)
        tool.tool_type = "DbFileOutput"
        tool.configuration = MagicMock(spec=ToolConfiguration)
        tool.configuration.parsed = {"file_path": tgt}

        # Mock output fields
        mock_fields = []
        for col in output_columns:
            f = MagicMock()
            f.name = col
            mock_fields.append(f)
        tool.output_fields = mock_fields
        res.workflow.tools[tid] = tool

    # Business summary
    bs = MagicMock(spec=WorkflowBusinessSummary)
    bs.business_purpose = business_purpose
    bs.business_outputs = []
    bs.source_inputs = []
    res.business_summary = bs

    # Metrics
    res.metrics = MagicMock()
    res.metrics.total_connections = 0

    res.sttm = None
    return res


class TestBusinessAreaSegregation:
    """TestSuite for business area segregation and classification accuracy."""

    def test_case_1_all_business_areas_populated(self):
        """Case 1: All business areas populated with workflows."""
        wf_claims = _make_dummy_canonical_result(
            "wf_1", "Claims.yxmd",
            business_purpose="Processes insurance claim losses and claimant exposure.",
            target_files=["Claims_Loss.xlsx"], output_columns=["Claim_ID", "Loss_Amount"]
        )
        wf_legal = _make_dummy_canonical_result(
            "wf_2", "Legal.yxmd",
            business_purpose="Tracks litigation matters, contracts, and legal arbitration proceedings.",
            target_files=["Litigation.xlsx"], output_columns=["Matter_ID", "Litigation_Status"]
        )
        wf_uw = _make_dummy_canonical_result(
            "wf_3", "Underwriting.yxmd",
            business_purpose="Evaluates policy underwriting eligibility, coverage limits, and premium calculations.",
            target_files=["Policy_Underwriting.xlsx"], output_columns=["Policy_ID", "Premium"]
        )
        wf_sales = _make_dummy_canonical_result(
            "wf_4", "Sales.yxmd",
            business_purpose="Monitors product sales revenue, customer order pipelines, and distributor channels.",
            target_files=["Sales_Revenue.xlsx"], output_columns=["Sales_Amount", "Commission"]
        )

        portfolio = build_portfolio_analysis([
            ("Claims.yxmd", "Claims.yxmd", wf_claims),
            ("Legal.yxmd", "Legal.yxmd", wf_legal),
            ("Underwriting.yxmd", "Underwriting.yxmd", wf_uw),
            ("Sales.yxmd", "Sales.yxmd", wf_sales),
        ])

        # Verify all 4 configured business areas are present
        assert len(portfolio.business_areas) == 4
        counts = portfolio.business_area_counts
        for area in ALLOWED_BUSINESS_AREAS:
            assert counts[area] == 1

        # Verify business_areas objects
        for group in portfolio.business_areas:
            assert group.workflow_count == 1
            assert len(group.workflows) == 1

    def test_case_2_some_business_areas_empty(self):
        """Case 2: Empty business areas are still materialised as cards with count 0."""
        wf_claims_1 = _make_dummy_canonical_result(
            "wf_1", "Claims1.yxmd",
            business_purpose="Analyses claim exposure and fraud scores.",
            target_files=["Claims_Extract.xlsx"], output_columns=["Claim_ID", "Fraud_Score"]
        )
        wf_claims_2 = _make_dummy_canonical_result(
            "wf_2", "Claims2.yxmd",
            business_purpose="Reports subrogation and loss indemnity recoveries.",
            target_files=["Subrogation.xlsx"], output_columns=["Loss_Ratio", "Indemnity"]
        )
        wf_sales = _make_dummy_canonical_result(
            "wf_3", "Sales.yxmd",
            business_purpose="Tracks distributor sales performance and commissions.",
            target_files=["Sales.xlsx"], output_columns=["Sales_Amount", "Distributor"]
        )

        portfolio = build_portfolio_analysis([
            ("Claims1.yxmd", "Claims1.yxmd", wf_claims_1),
            ("Claims2.yxmd", "Claims2.yxmd", wf_claims_2),
            ("Sales.yxmd", "Sales.yxmd", wf_sales),
        ])

        # All 4 configured business areas MUST be present
        area_names = [g.business_area for g in portfolio.business_areas]
        for area in ALLOWED_BUSINESS_AREAS:
            assert area in area_names

        # Legal and Underwriting have 0 workflows
        assert portfolio.business_area_counts["Legal"] == 0
        assert portfolio.business_area_counts["Underwriting"] == 0
        assert portfolio.business_area_counts["Claims & Risk"] == 2
        assert portfolio.business_area_counts["Sales & Distribution"] == 1

        legal_group = next(g for g in portfolio.business_areas if g.business_area == "Legal")
        assert legal_group.workflow_count == 0
        assert legal_group.workflows == []

        uw_group = next(g for g in portfolio.business_areas if g.business_area == "Underwriting")
        assert uw_group.workflow_count == 0
        assert uw_group.workflows == []

    def test_case_3_all_business_areas_empty(self):
        """Case 3: When portfolio has 0 workflows, all business areas are still materialised."""
        portfolio = build_portfolio_analysis([])

        assert len(portfolio.business_areas) == 4
        for group in portfolio.business_areas:
            assert group.workflow_count == 0
            assert group.workflows == []
            assert group.business_area in ALLOWED_BUSINESS_AREAS

        for area in ALLOWED_BUSINESS_AREAS:
            assert portfolio.business_area_counts[area] == 0

    def test_case_4_llm_successfully_classifies(self):
        """Case 4: LLM receives business purpose in prompt and classifies accurately."""
        wf = _make_dummy_canonical_result(
            "wf_commercial", "Commercial_Analytics.yxmd",
            business_purpose="Identifies commercial growth opportunities, customer retention rates, and marketing pipeline trends.",
            target_files=["Output_Table.xlsx"], output_columns=["Metric_Value"]
        )

        prompts_received = []

        def mock_llm_generator(sys_prompt: str, user_prompt: str) -> str:
            prompts_received.append((sys_prompt, user_prompt))
            return json.dumps({
                "workflow_classifications": [
                    {
                        "workflow_id": "wf_commercial",
                        "business_area": "Sales & Distribution",
                        "confidence": "HIGH",
                        "reasoning": "Focuses on commercial growth, customer retention, and pipeline analysis.",
                        "evidence": ["commercial growth", "customer retention"],
                        "secondary_business_areas": [],
                    }
                ]
            })

        fake_client = FakeLLMClient(generator_fn=mock_llm_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf], generator=gen)

        # Verify prompt received business purpose
        assert len(prompts_received) == 1
        _, user_p = prompts_received[0]
        assert "Identifies commercial growth opportunities" in user_p
        assert "AVAILABLE BUSINESS AREAS & DEFINITIONS" in user_p

        # Verify classification
        assert classifications["wf_commercial"].business_area == "Sales & Distribution"
        assert classifications["wf_commercial"].classification_source == "llm"
        assert classifications["wf_commercial"].confidence == "HIGH"

    def test_case_5_llm_fails_graceful_fallback(self):
        """Case 5: When LLM fails/times out, deterministic fallback classifies every workflow."""
        wf = _make_dummy_canonical_result(
            "wf_legal", "Contract_Review.yxmd",
            business_purpose="Manages contract disputes, arbitration clauses, and regulatory compliance disclosures.",
            target_files=["Matters.xlsx"], output_columns=["Matter_ID", "Contract_ID"]
        )

        def failing_generator(sys_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("Azure OpenAI rate limit 429")

        fake_client = FakeLLMClient(generator_fn=failing_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf], generator=gen)

        assert "wf_legal" in classifications
        assert classifications["wf_legal"].business_area == "Legal"
        assert classifications["wf_legal"].classification_source == "deterministic_fallback"

    def test_case_6_partial_llm_response(self):
        """Case 6: Missing workflows from partial LLM response are resolved via deterministic fallback."""
        wf1 = _make_dummy_canonical_result(
            "wf_1", "Claims.yxmd",
            business_purpose="Monitors claim frequency and loss reserves.",
            target_files=["Claims.xlsx"], output_columns=["Claim_ID", "Loss_Amount"]
        )
        wf2 = _make_dummy_canonical_result(
            "wf_2", "Legal.yxmd",
            business_purpose="Processes legal contract disputes and litigation matters.",
            target_files=["Legal.xlsx"], output_columns=["Matter_ID", "Litigation_Status"]
        )

        # LLM only returns classification for wf_1, omitting wf_2
        def partial_generator(sys_prompt: str, user_prompt: str) -> str:
            return json.dumps({
                "workflow_classifications": [
                    {
                        "workflow_id": "wf_1",
                        "business_area": "Claims & Risk",
                        "confidence": "HIGH",
                        "reasoning": "Processes claims and losses.",
                        "evidence": ["Claim_ID"],
                    }
                ]
            })

        fake_client = FakeLLMClient(generator_fn=partial_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf1, wf2], generator=gen)

        assert len(classifications) == 2
        # wf_1 from LLM
        assert classifications["wf_1"].business_area == "Claims & Risk"
        assert classifications["wf_1"].classification_source == "llm"
        # wf_2 from deterministic fallback
        assert classifications["wf_2"].business_area == "Legal"
        assert classifications["wf_2"].classification_source == "deterministic_fallback"

    def test_case_7_invalid_business_area_rejected(self):
        """Case 7: LLM returning an unrecognised business area is rejected and falls back."""
        wf = _make_dummy_canonical_result(
            "wf_1", "Ledger.yxmd",
            business_purpose="Generates general ledger journal vouchers and account reconciliations.",
            target_files=["GL_Summary.xlsx"], output_columns=["Account_Number"]
        )

        def invalid_area_generator(sys_prompt: str, user_prompt: str) -> str:
            return json.dumps({
                "workflow_classifications": [
                    {
                        "workflow_id": "wf_1",
                        "business_area": "Finance & Accounting",  # INVALID AREA
                        "confidence": "HIGH",
                        "reasoning": "Accounting tasks.",
                        "evidence": ["GL_Summary.xlsx"],
                    }
                ]
            })

        fake_client = FakeLLMClient(generator_fn=invalid_area_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf], generator=gen)

        assert classifications["wf_1"].business_area != "Finance & Accounting"
        assert classifications["wf_1"].classification_source == "deterministic_fallback"

    def test_case_8_unknown_workflow_id_rejected(self):
        """Case 8: LLM returning unknown workflow IDs are rejected with no phantom workflows."""
        wf = _make_dummy_canonical_result(
            "real_wf_1", "Underwriting.yxmd",
            business_purpose="Calculates policy binder risk rating and premium values.",
            target_files=["Policy.xlsx"], output_columns=["Policy_ID", "Premium"]
        )

        def unknown_id_generator(sys_prompt: str, user_prompt: str) -> str:
            return json.dumps({
                "workflow_classifications": [
                    {
                        "workflow_id": "phantom_wf_999",  # UNKNOWN ID
                        "business_area": "Claims & Risk",
                        "confidence": "HIGH",
                    },
                    {
                        "workflow_id": "real_wf_1",
                        "business_area": "Underwriting",
                        "confidence": "HIGH",
                        "reasoning": "Policy underwriting.",
                        "evidence": ["Premium"],
                    }
                ]
            })

        fake_client = FakeLLMClient(generator_fn=unknown_id_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf], generator=gen)

        # Must NOT contain phantom_wf_999
        assert "phantom_wf_999" not in classifications
        assert len(classifications) == 1
        assert classifications["real_wf_1"].business_area == "Underwriting"

    def test_case_9_business_purpose_driven_classification(self):
        """Case 9: Business purpose overrides superficial table/column naming signals."""
        # The file has a generic/confusing name and column, but business purpose is unambiguously Claims & Risk
        wf = _make_dummy_canonical_result(
            "wf_disputed_data", "General_Extract.yxmd",
            business_purpose="Performs automated claims fraud investigation, loss exposure forecasting, and litigation reserve calculation.",
            target_files=["Data_Extract.xlsx"], output_columns=["Row_ID", "Status_Code"]
        )

        def smart_llm(sys_prompt: str, user_prompt: str) -> str:
            # LLM reads the business purpose and correctly assigns Claims & Risk
            assert "fraud investigation, loss exposure forecasting" in user_prompt
            return json.dumps({
                "workflow_classifications": [
                    {
                        "workflow_id": "wf_disputed_data",
                        "business_area": "Claims & Risk",
                        "confidence": "HIGH",
                        "reasoning": "Business purpose explicitly states claims fraud investigation and loss exposure.",
                        "evidence": ["fraud investigation", "loss exposure"],
                    }
                ]
            })

        fake_client = FakeLLMClient(generator_fn=smart_llm)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        classifications = classify_portfolio_business_areas([wf], generator=gen)
        assert classifications["wf_disputed_data"].business_area == "Claims & Risk"
        assert classifications["wf_disputed_data"].classification_source == "llm"

    def test_case_10_count_invariant(self):
        """Case 10: Sum of card workflow counts strictly equals total classified workflows."""
        workflows = [
            _make_dummy_canonical_result(f"wf_{i}", f"Wf_{i}.yxmd", business_purpose="Arbitrary ETL process")
            for i in range(10)
        ]

        portfolio = build_portfolio_analysis([
            (f"Wf_{i}.yxmd", f"Wf_{i}.yxmd", wf) for i, wf in enumerate(workflows)
        ])

        # Invariant 1: Sum of business_area_counts equals total successful workflows
        total_counts = sum(portfolio.business_area_counts.values())
        assert total_counts == 10

        # Invariant 2: Sum of group workflow_counts equals total workflows
        total_group_counts = sum(g.workflow_count for g in portfolio.business_areas)
        assert total_group_counts == 10

        # Invariant 3: All 10 workflows appear exactly once across all business areas
        seen_workflow_ids = set()
        for group in portfolio.business_areas:
            for w in group.workflows:
                assert w.workflow_id not in seen_workflow_ids
                seen_workflow_ids.add(w.workflow_id)
        assert len(seen_workflow_ids) == 10
