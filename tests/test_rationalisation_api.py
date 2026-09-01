"""Tests for the ETL Rationalisation REST API endpoint and LLM infrastructure reuse."""

from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile
import pytest
from starlette.testclient import TestClient

from awa.llm.client import FakeLLMClient, set_default_llm_client
from awa.llm.generator import LLMNarrativeGenerator, set_default_generator
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_portfolio_id(client):
    """Upload a real multi-workflow portfolio and return its ID."""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("Claims.yxmd", Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes())
        zf.writestr("FTSE.yxmd", Path("FTSE 100.yxmd").read_bytes())
        zf.writestr("Food1.yxmd", Path("BBCFoodAggr.yxmd").read_bytes())
        zf.writestr("Food2.yxmd", Path("BBCFood v2.yxmd").read_bytes())
        zf.writestr("Filter.yxmd", Path("fixtures/basic/simple_filter.yxmd").read_bytes())
    zip_buf.seek(0)

    resp = client.post(
        "/api/portfolio/upload",
        files={"files": ("estate.zip", zip_buf.getvalue(), "application/zip")},
        data={"portfolio_name": "Test Estate"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "portfolio_id" in data
    return data["portfolio_id"]


class TestRationalisationAPI:
    """Test ETL Rationalisation API endpoint stability, schema conformance, and LLM fallback."""

    def test_rationalisation_endpoint_with_llm_disabled_returns_200(self, client, sample_portfolio_id):
        """When LLM is unavailable/disabled, endpoint must return HTTP 200 with deterministic results."""
        FakeLLMClient.is_available = property(lambda self: True)

        class UnavailableClient(FakeLLMClient):
            @property
            def is_available(self) -> bool:
                return False

        fake_client = UnavailableClient(model_name="mock")
        gen = LLMNarrativeGenerator(client=fake_client)
        set_default_generator(gen)

        try:
            resp = client.get(f"/api/portfolio/{sample_portfolio_id}/rationalisation?use_llm=true")
            assert resp.status_code == 200, f"Failed with {resp.status_code}: {resp.text}"

            data = resp.json()
            assert data["portfolio_id"] == sample_portfolio_id
            assert data["analysed_workflow_count"] >= 5
            assert "candidates" in data
            assert "recommendation_counts" in data
            assert "total_opportunities" in data
            assert data["total_opportunities"] == len(data["candidates"])

            # Verify candidates adhere to DTO structure
            for cand in data["candidates"]:
                assert "candidate_id" in cand
                assert "workflow_ids" in cand
                assert "workflow_names" in cand
                assert cand["recommendation_type"] in ["CONSOLIDATE", "RETIRE_CANDIDATE", "SHARED_LOGIC", "REVIEW"]
                assert cand["confidence"] in ["HIGH", "MEDIUM", "LOW"]
                assert 0.0 <= cand["opportunity_score"] <= 100.0
                assert cand["llm_enrichment_status"] == "DETERMINISTIC_BASELINE"
                assert "deterministic_metrics" in cand
                assert "output_evidence" in cand
                assert "dependency_evidence" in cand
                assert "risk_context" in cand
        finally:
            set_default_generator(None)

    def test_rationalisation_with_use_llm_false(self, client, sample_portfolio_id):
        """When use_llm=false is requested, returns fast-path deterministic baseline."""
        resp = client.get(f"/api/portfolio/{sample_portfolio_id}/rationalisation?use_llm=false")
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_id"] == sample_portfolio_id
        for cand in data["candidates"]:
            assert cand["llm_enrichment_status"] == "DETERMINISTIC_BASELINE"

    def test_rationalisation_with_llm_enrichment_success(self, client, sample_portfolio_id):
        """When LLM is available and valid, candidate reasoning is enriched."""
        fake_client = FakeLLMClient(
            model_name="mock-active",
            default_response=json.dumps({
                "recommendation": "CONSOLIDATE",
                "reasoning": "Mock AI architectural analysis: both pipelines share common upstream ingestion.",
                "proposed_strategy": "Centralize ingestion into a shared module.",
                "validation_requirements": ["Verify batch SLA", "Check target endpoints"],
            }),
        )
        gen = LLMNarrativeGenerator(client=fake_client)
        set_default_generator(gen)

        try:
            resp = client.get(f"/api/portfolio/{sample_portfolio_id}/rationalisation?use_llm=true")
            assert resp.status_code == 200
            data = resp.json()
            # If candidates exist that allow CONSOLIDATE, they should be marked ENRICHED
            consolidate_cands = [c for c in data["candidates"] if "CONSOLIDATE" in c["admissible_recommendations"]]
            if consolidate_cands:
                enriched = [c for c in consolidate_cands if c["llm_enrichment_status"] == "ENRICHED"]
                assert len(enriched) > 0
                assert "Mock AI architectural analysis" in enriched[0]["reasoning"]
        finally:
            set_default_generator(None)

    def test_rationalisation_with_llm_exception_falls_back_gracefully(self, client, sample_portfolio_id):
        """When LLM client raises an exception during generation, endpoint falls back to deterministic without 500."""
        def raise_error(sys_prompt, user_prompt):
            raise ConnectionError("Azure endpoint connection timeout")

        fake_client = FakeLLMClient(model_name="mock-failing", generator_fn=raise_error)
        gen = LLMNarrativeGenerator(client=fake_client)
        set_default_generator(gen)

        try:
            resp = client.get(f"/api/portfolio/{sample_portfolio_id}/rationalisation?use_llm=true")
            # Must return 200, never 500!
            assert resp.status_code == 200
            data = resp.json()
            for cand in data["candidates"]:
                assert cand["llm_enrichment_status"] in ["DETERMINISTIC_BASELINE", "DETERMINISTIC_FALLBACK"]
        finally:
            set_default_generator(None)

    def test_missing_portfolio_returns_404(self, client):
        """Non-existent portfolio ID must return HTTP 404."""
        resp = client.get("/api/portfolio/non_existent_portfolio_999/rationalisation")
        assert resp.status_code == 404

    def test_default_azure_llm_config_is_disabled_and_rationalisation_succeeds(self, client, sample_portfolio_id):
        """In default deployment state (where Azure env vars are not provided or enabled=False),
        the endpoint succeeds with HTTP 200 and deterministic rationalisation analysis without 500."""
        # Ensure default generator is restored
        set_default_generator(None)

        resp = client.get(f"/api/portfolio/{sample_portfolio_id}/rationalisation?use_llm=true")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["portfolio_id"] == sample_portfolio_id
        assert data["analysed_workflow_count"] >= 5
        assert len(data["candidates"]) > 0
        for cand in data["candidates"]:
            assert cand["llm_enrichment_status"] == "DETERMINISTIC_BASELINE"
            assert cand["opportunity_score"] > 0
            assert cand["recommendation_type"] in ["CONSOLIDATE", "RETIRE_CANDIDATE", "SHARED_LOGIC", "REVIEW"]

