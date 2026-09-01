"""Tests for Business-Area Portfolio Classification.

Validates:
1. Strict evidence boundary: classifier payload receives ONLY production output datasets and column headers.
2. Complete exclusion of forbidden evidence: workflow names, workflow IDs, source datasets, business summaries, tool names.
3. Deterministic classification across the 4 domains:
   - Claims & Risk
   - Legal
   - Underwriting
   - Sales & Distribution
4. Rejection of hallucinated evidence tokens.
5. Rejection of unsupported business areas.
6. Graceful deterministic fallback on LLM failure, timeout, or malformed JSON.
7. Workflows without production outputs are classified as UNCLASSIFIED.
8. Multiple output files aggregation at workflow level.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from awa.analysis.business_area_classifier import (
    ALLOWED_BUSINESS_AREAS,
    classify_business_area_deterministic,
    classify_workflow_business_area,
    extract_output_evidence_for_workflow,
)
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.llm.cache import LLMNarrativeCache
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.portfolio import BusinessAreaClassification


class TestBusinessAreaClassification:
    """Test suite for business-area domain classification and strict evidence boundaries."""

    def test_claims_and_risk_deterministic_classification(self):
        """Requirement 27: Claims & Risk domain evidence correctly classified."""
        evidence = [
            {
                "dataset": "Claims_Risk.xlsx",
                "columns": ["Claim_ID", "Risk_Percentage", "Fraud_Score", "Loss_Ratio"],
            }
        ]
        result = classify_business_area_deterministic(evidence)
        assert result.business_area == "Claims & Risk"
        assert result.confidence in ("HIGH", "MEDIUM")
        assert "Risk_Percentage" in result.evidence or "Fraud_Score" in result.evidence or "Claims_Risk.xlsx" in result.evidence

    def test_legal_deterministic_classification(self):
        """Requirement 27: Legal domain evidence correctly classified."""
        evidence = [
            {
                "dataset": "Legal_Matters.xlsx",
                "columns": ["Matter_ID", "Contract_ID", "Litigation_Status", "Court_Date"],
            }
        ]
        result = classify_business_area_deterministic(evidence)
        assert result.business_area == "Legal"
        assert result.confidence in ("HIGH", "MEDIUM")
        assert any(ev in result.evidence for ev in ["Matter_ID", "Contract_ID", "Litigation_Status", "Legal_Matters.xlsx"])

    def test_underwriting_deterministic_classification(self):
        """Requirement 27: Underwriting domain evidence correctly classified."""
        evidence = [
            {
                "dataset": "Policy_Underwriting.xlsx",
                "columns": ["Policy_ID", "Applicant_ID", "Coverage", "Premium", "Underwriting_Status"],
            }
        ]
        result = classify_business_area_deterministic(evidence)
        assert result.business_area == "Underwriting"
        assert result.confidence in ("HIGH", "MEDIUM")
        assert any(ev in result.evidence for ev in ["Policy_ID", "Coverage", "Premium", "Policy_Underwriting.xlsx"])

    def test_sales_and_distribution_deterministic_classification(self):
        """Requirement 27: Sales & Distribution domain evidence correctly classified."""
        evidence = [
            {
                "dataset": "Sales_Distribution.xlsx",
                "columns": ["Customer_ID", "Sales_Amount", "Distributor", "Sales_Channel", "Commission"],
            }
        ]
        result = classify_business_area_deterministic(evidence)
        assert result.business_area == "Sales & Distribution"
        assert result.confidence in ("HIGH", "MEDIUM")
        assert any(ev in result.evidence for ev in ["Customer_ID", "Sales_Amount", "Distributor", "Sales_Distribution.xlsx"])

    def test_forbidden_evidence_boundary(self):
        """Requirement 29: Classifier payload contains ONLY output datasets and columns.

        Asserts that workflow filename, workflow ID, source datasets, business purpose,
        tool names, annotations, and STTM mappings are NEVER present in the LLM payload.
        """
        canonical_res = analyze_canonical(Path("FTSE 100.yxmd"))
        evidence = extract_output_evidence_for_workflow(canonical_res)

        # Build payload as passed to LLM
        payload_str = json.dumps({"outputs": evidence})

        # Forbidden tokens that MUST NOT appear
        assert canonical_res.analysis_id not in payload_str
        assert "FTSE 100.yxmd" not in payload_str
        assert canonical_res.source.original_filename not in payload_str

        # No source datasets in output evidence
        if canonical_res.business_summary:
            for inp in canonical_res.business_summary.source_inputs:
                if inp.source_filename:
                    assert inp.source_filename not in [out["dataset"] for out in evidence]

        # No workflow business purpose
        if canonical_res.business_summary and canonical_res.business_summary.business_purpose:
            assert canonical_res.business_summary.business_purpose not in payload_str

        # Every top-level key in each output entry must only be 'dataset', 'columns', or 'table_or_sheet'
        for out in evidence:
            allowed_keys = {"dataset", "columns", "table_or_sheet"}
            assert set(out.keys()).issubset(allowed_keys)
            assert isinstance(out["dataset"], str)
            assert isinstance(out["columns"], list)

    def test_hallucination_rejection(self):
        """Requirement 28: LLM response containing hallucinated evidence is rejected and falls back."""
        evidence = [
            {
                "dataset": "Claims_Risk.xlsx",
                "columns": ["Claim_ID", "Risk_Percentage", "Loss_Ratio"],
            }
        ]

        # LLM invents "Fake_Risk_Field" not present in actual columns
        def hallucinating_generator(sys_prompt: str, user_prompt: str) -> str:
            return json.dumps({
                "business_area": "Claims & Risk",
                "confidence": "HIGH",
                "evidence": ["Fake_Risk_Field"],  # HALLUCINATED
            })

        fake_client = FakeLLMClient(generator_fn=hallucinating_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        # Create dummy CanonicalAnalysisResult
        dummy_res = MagicMock()
        dummy_res.workflow.tools = {}
        dummy_res.graph.nodes = []

        # Patch extraction
        import awa.analysis.business_area_classifier as bac
        orig_extract = bac.extract_output_evidence_for_workflow
        try:
            bac.extract_output_evidence_for_workflow = lambda r: evidence
            classified = classify_workflow_business_area(dummy_res, generator=gen)

            # Hallucinated LLM response must be rejected -> source is deterministic_fallback
            assert classified.classification_source == "deterministic_fallback"
            assert "Fake_Risk_Field" not in classified.evidence
            assert classified.business_area == "Claims & Risk"  # from deterministic fallback
        finally:
            bac.extract_output_evidence_for_workflow = orig_extract

    def test_unsupported_business_area_rejection(self):
        """Requirement 17: LLM proposing unsupported business areas is rejected and falls back."""
        evidence = [
            {
                "dataset": "Finance_General_Ledger.xlsx",
                "columns": ["Account_ID", "Debit", "Credit"],
            }
        ]

        def invalid_area_generator(sys_prompt: str, user_prompt: str) -> str:
            return json.dumps({
                "business_area": "Finance",  # NOT in ALLOWED_BUSINESS_AREAS
                "confidence": "HIGH",
                "evidence": ["Finance_General_Ledger.xlsx"],
            })

        fake_client = FakeLLMClient(generator_fn=invalid_area_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        dummy_res = MagicMock()
        import awa.analysis.business_area_classifier as bac
        orig_extract = bac.extract_output_evidence_for_workflow
        try:
            bac.extract_output_evidence_for_workflow = lambda r: evidence
            classified = classify_workflow_business_area(dummy_res, generator=gen)

            # Invalid area rejected
            assert classified.business_area != "Finance"
            assert classified.classification_source == "deterministic_fallback"
        finally:
            bac.extract_output_evidence_for_workflow = orig_extract

    def test_llm_failure_graceful_fallback(self):
        """Requirement 30: Timeouts, HTTP failures, and malformed JSON fallback gracefully."""
        evidence = [
            {
                "dataset": "Legal_Matters.xlsx",
                "columns": ["Matter_ID", "Litigation_Status"],
            }
        ]

        def error_generator(sys_prompt: str, user_prompt: str) -> str:
            raise RuntimeError("Connection timed out after 30s")

        fake_client = FakeLLMClient(generator_fn=error_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())

        dummy_res = MagicMock()
        import awa.analysis.business_area_classifier as bac
        orig_extract = bac.extract_output_evidence_for_workflow
        try:
            bac.extract_output_evidence_for_workflow = lambda r: evidence
            classified = classify_workflow_business_area(dummy_res, generator=gen)

            assert classified.business_area == "Legal"
            assert classified.classification_source == "deterministic_fallback"
        finally:
            bac.extract_output_evidence_for_workflow = orig_extract

    def test_no_output_workflow_unclassified(self):
        """Requirement 31: Workflows without production outputs are classified as UNCLASSIFIED."""
        # BBCFoodAggr terminates only in BrowseV2 (inspection sink)
        canonical_res = analyze_canonical(Path("BBCFoodAggr.yxmd"))
        evidence = extract_output_evidence_for_workflow(canonical_res)
        assert len(evidence) == 0  # 0 production outputs

        classified = classify_workflow_business_area(canonical_res)
        assert classified.business_area == "UNCLASSIFIED"
        assert classified.confidence == "UNCLASSIFIED"
        assert len(classified.evidence) == 0
        assert classified.classification_source == "deterministic_fallback"

    def test_workflow_name_and_sources_not_used(self):
        """Requirement 11 & 12: Classifier does not use workflow names or source datasets."""
        # Workflow is named "Claims_Risk_Workflow.yxmd" with source "Claims_Master.xlsx",
        # BUT output is "Sales_Report.xlsx" with columns ["Customer_ID", "Sales_Amount"]
        evidence = [
            {
                "dataset": "Sales_Report.xlsx",
                "columns": ["Customer_ID", "Sales_Amount", "Revenue"],
            }
        ]
        classified = classify_business_area_deterministic(evidence)
        # MUST classify as Sales & Distribution based on output, NOT Claims & Risk
        assert classified.business_area == "Sales & Distribution"
        assert classified.business_area != "Claims & Risk"

    def test_multiple_outputs_workflow_aggregation(self):
        """Requirement 7 & 8: Multiple output files considered and aggregated at workflow level."""
        evidence = [
            {
                "dataset": "Claims_Risk.xlsx",
                "columns": ["Claim_ID", "Risk_Percentage", "Fraud_Score"],
            },
            {
                "dataset": "Policy_Exposure.xlsx",
                "columns": ["Policy_ID", "Coverage", "Premium"],
            },
        ]
        classified = classify_business_area_deterministic(evidence)
        # Top domain is Claims & Risk or Underwriting, other is secondary
        assert classified.business_area in ("Claims & Risk", "Underwriting")
        assert len(classified.secondary_business_areas) > 0

    def test_portfolio_business_area_aggregation(self):
        """Requirement 15: Portfolio aggregates business area counts deterministically."""
        claims_res = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        ftse_res = analyze_canonical(Path("FTSE 100.yxmd"))

        portfolio = build_portfolio_analysis([
            ("Claims.yxmd", "Claims.yxmd", claims_res),
            ("FTSE.yxmd", "FTSE.yxmd", ftse_res),
        ])

        assert "business_area_counts" in portfolio.to_dict()
        counts = portfolio.business_area_counts
        # All 4 configured areas present in counts
        for area in ALLOWED_BUSINESS_AREAS:
            assert area in counts
        assert sum(counts.values()) == 2
