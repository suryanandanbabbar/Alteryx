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

    def test_criticality_semantic_impact_boosts(self):
        """Criticality increases when business purpose evidences deliverables, scope, customer, client impact."""
        ctx = PortfolioDependencyContext()
        base = calculate_workflow_criticality(
            workflow_id="wf_test",
            workflow_filename="Test.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            business_purpose="Standard data processing workflow.",
        )

        enhanced = calculate_workflow_criticality(
            workflow_id="wf_test",
            workflow_filename="Test.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            business_purpose=(
                "This enterprise-wide workflow processes claimant coverage decisions and "
                "adjudicates policyholder indemnity payments for auto and property insurance."
            ),
        )

        assert enhanced.score > base.score
        assert enhanced.breakdown["business_purpose_impact"] == 8.0  # +4 for scope, +4 for customer
        assert any("customer/claimant" in f.lower() for f in enhanced.factors)
        assert any("scope" in f.lower() for f in enhanced.factors)

    def test_criticality_anti_double_counting_guard(self):
        """Repeating the same impact keyword multiple times counts at most once per dimension."""
        ctx = PortfolioDependencyContext()
        repetitive_purpose = (
            "Processes customer benefits. Handles customer payments for customer accounts. "
            "Supports claimant coverage and claimant settlement outcomes."
        )

        assessment = calculate_workflow_criticality(
            workflow_id="wf_anti_dc",
            workflow_filename="Anti_DC.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            business_purpose=repetitive_purpose,
        )

        # Customer impact flag must count only once (+4.0)
        assert assessment.breakdown["business_purpose_impact"] == 4.0
        customer_factors = [f for f in assessment.factors if "customer" in f.lower()]
        assert len(customer_factors) == 1

    def test_criticality_non_impact_produces_zero_boost(self):
        """Arbitrary technical or incidental text does not trigger false positive criticality boosts."""
        ctx = PortfolioDependencyContext()
        neutral_purpose = "Internal utility script that parses xml tags and verifies syntax formatting."

        assessment = calculate_workflow_criticality(
            workflow_id="wf_neutral",
            workflow_filename="Neutral.yxmd",
            sources=["input.csv"],
            targets=["output.xlsx"],
            inspection_sinks=[],
            context=ctx,
            business_purpose=neutral_purpose,
        )

        assert assessment.breakdown["business_purpose_impact"] == 0.0
        assert not any("business purpose" in f.lower() for f in assessment.factors)
