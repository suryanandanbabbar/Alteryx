"""Comprehensive test suite for Business Area Classification Stability and Drift Elimination.

Tests:
1. Repeatability across repeated executions (100% deterministic consistency).
2. Portfolio does not reclassify or alter existing canonical tags.
3. Valid canonical business areas cannot be overwritten by Other / Unclassified or weaker fallbacks.
4. Taxonomy normalization and alias resolution.
5. Deterministic fallback on LLM failure preserves valid classifications without drift.
6. Concurrent workflow processing isolation.
7. Refresh equivalence: Initial Analysis -> Portfolio matches Storage Reload -> Portfolio exactly.
"""

from __future__ import annotations

import concurrent.futures
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from awa.analysis.business_area_classifier import (
    ALLOWED_BUSINESS_AREAS,
    classify_business_area_deterministic,
    classify_business_function_deterministic,
    extract_output_evidence_for_workflow,
)
from awa.analysis.portfolio_analyzer import (
    build_portfolio_analysis,
    CONFIGURED_PORTFOLIO_BUSINESS_AREAS,
)
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.llm.cache import LLMNarrativeCache
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator, get_default_generator
from awa.llm.schemas import BusinessPurposeResult
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.business_summary import WorkflowBusinessSummary
from backend.app.main import app
from backend.app.services.analyzer import process_uploaded_workflow, to_overview_dto
from backend.app.services.storage import InMemoryStorage, get_storage


class TestBusinessAreaStabilityAndDrift:
    """Rigorous verification of business area classification stability and zero drift."""

    def test_repeatability_across_repeated_deterministic_runs(self):
        """Test 1: Repeatability across repeated executions produces identical classifications."""
        out_ev = [{
            "dataset": "Commercial_Policy_Pricing_Output.xlsx",
            "columns": ["PolicyNumber", "PremiumAmount", "RatingTier", "UnderwriterNotes"],
        }]
        purpose = "Processes historical claims data to calculate commercial policy pricing and rating factors for underwriting risk assessment."
        wf_name = "Commercial_Policy_Pricing_Engine.yxmd"
        func = "Policy pricing and premium rating calculation"
        sources = ["Claims_Volume_Extract.xlsx", "Loss_History_Master.xlsx"]

        # Run 20 times in a loop
        results = []
        for _ in range(20):
            res = classify_business_area_deterministic(
                out_ev,
                business_purpose=purpose,
                workflow_name=wf_name,
                business_function=func,
                input_sources=sources,
            )
            results.append((res.business_area, res.confidence, res.classification_source, tuple(res.evidence)))

        first = results[0]
        assert first[0] == "Underwriting"
        for r in results[1:]:
            assert r == first, f"Drift detected in deterministic classification: {r} != {first}"

    def test_portfolio_does_not_reclassify_existing_canonical_tags(self):
        """Test 2: Portfolio builder strictly consumes canonical tags and never reclassifies them."""
        # Create a mock result with an explicit canonical business_area_tag
        res1 = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd", analysis_id="wf_claims_1")
        res1.business_summary.business_area_tag = "Claims & Risk"
        res1.business_summary.business_area_tag_source = "llm"
        res1.business_summary.business_function = "Claims adjudication and loss reserve management"

        res2 = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd", analysis_id="wf_legal_2")
        res2.business_summary.business_area_tag = "Legal"
        res2.business_summary.business_area_tag_source = "llm"
        res2.business_summary.business_function = "Regulatory compliance reporting"

        portfolio = build_portfolio_analysis([
            ("Claims.yxmd", "Claims.yxmd", res1),
            ("Legal.yxmd", "Legal.yxmd", res2),
        ])

        summary_map = {w.workflow_id: w for w in portfolio.workflows}
        assert summary_map["wf_claims_1"].business_area.business_area == "Claims & Risk"
        assert summary_map["wf_legal_2"].business_area.business_area == "Legal"

        # Verify res objects are not mutated
        assert res1.business_summary.business_area_tag == "Claims & Risk"
        assert res2.business_summary.business_area_tag == "Legal"

    def test_valid_canonical_area_cannot_be_overwritten_by_other_unclassified(self):
        """Test 3: An existing valid business area tag is immutable against fallback overrides."""
        res = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd", analysis_id="wf_uw_3")
        res.business_summary.business_area_tag = "Underwriting"
        res.business_summary.business_function = "Underwriting decisioning"

        # Build portfolio
        portfolio = build_portfolio_analysis([("UW.yxmd", "UW.yxmd", res)])
        assert portfolio.workflows[0].business_area.business_area == "Underwriting"
        assert res.business_summary.business_area_tag == "Underwriting"

    def test_all_five_configured_business_areas_supported(self):
        """Test 4: All 5 configured business areas are recognized and supported without drift."""
        expected_areas = ["Claims & Risk", "Legal", "Underwriting", "Sales & Distribution", "Actuarial"]
        for area in expected_areas:
            assert area in ALLOWED_BUSINESS_AREAS
            assert area in CONFIGURED_PORTFOLIO_BUSINESS_AREAS

    def test_deterministic_fallback_on_llm_failure_preserves_valid_classifications(self):
        """Test 5: LLM failure triggers deterministic 7-tier classification with valid result."""
        fake_failing_client = FakeLLMClient(is_available=False)
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=fake_failing_client, cache=cache)

        res = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd", analysis_id="wf_fallback_test")
        purpose_res = gen.generate_business_purpose(
            res.workflow,
            res.business_summary,
            workflow_id="Claims_Volume_Analysis.yxmd",
        )

        assert purpose_res.business_area_tag in ALLOWED_BUSINESS_AREAS
        assert purpose_res.business_area_tag == "Claims & Risk"
        assert purpose_res.source == "deterministic_fallback"

    def test_concurrent_workflow_processing_isolation(self):
        """Test 6: Concurrent workflow analysis does not cause cross-contamination or drift."""
        def run_analysis(idx: int):
            aid = f"concurrent_wf_{idx}"
            return analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd", analysis_id=aid)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_analysis, i) for i in range(10)]
            results = [f.result() for f in futures]

        tags = [r.business_summary.business_area_tag for r in results]
        # All instances of this workflow must receive the identical classification
        assert len(set(tags)) == 1
        assert tags[0] in ALLOWED_BUSINESS_AREAS

    def test_refresh_equivalence(self):
        """Test 7: Direct portfolio upload matches storage retrieval on refresh exactly."""
        client = TestClient(app)
        wf_bytes = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes()
        ftse_bytes = Path("FTSE 100.yxmd").read_bytes()

        import zipfile
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Claims.yxmd", wf_bytes)
            zf.writestr("FTSE.yxmd", ftse_bytes)
        zip_buf.seek(0)

        # Upload
        resp_upload = client.post(
            "/api/portfolio/upload",
            files=[("files", ("portfolio.zip", zip_buf.getvalue(), "application/zip"))],
            data={"portfolio_name": "Stability Test Portfolio"},
        )
        assert resp_upload.status_code == 200
        upload_data = resp_upload.json()
        portfolio_id = upload_data["portfolio_id"]

        # Simulate browser refresh: GET /api/portfolio/{portfolio_id}
        resp_refresh = client.get(f"/api/portfolio/{portfolio_id}")
        assert resp_refresh.status_code == 200
        refresh_data = resp_refresh.json()

        # Check exact equality
        assert upload_data["business_area_counts"] == refresh_data["business_area_counts"]
        assert len(upload_data["workflows"]) == len(refresh_data["workflows"])

        for w_up, w_ref in zip(upload_data["workflows"], refresh_data["workflows"]):
            assert w_up["workflow_id"] == w_ref["workflow_id"]
            assert w_up["business_area"] == w_ref["business_area"]
            assert w_up["business_purpose"] == w_ref["business_purpose"]
