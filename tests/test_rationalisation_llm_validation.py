"""Deterministic unit tests for LLM Enrichment and Validation in ETL Rationalisation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from awa.analysis.rationalisation_analyzer import (
    enrich_candidate_with_llm,
    validate_llm_rationalisation_response,
)
from awa.model.portfolio import (
    DeterministicMetrics,
    RationalisationCandidate,
)


def _build_test_candidate(rec: str, admissible: list[str]) -> RationalisationCandidate:
    return RationalisationCandidate(
        candidate_id="cand_test_123",
        workflow_ids=["wf_a", "wf_b"],
        workflow_names=["Workflow_A.yxmd", "Workflow_B.yxmd"],
        recommendation_type=rec,
        confidence="HIGH",
        opportunity_score=75.0,
        reasoning="Deterministic baseline reasoning.",
        evidence=["Evidence item 1", "Evidence item 2"],
        shared_logic=["Filter: active=true", "Join on id"],
        unique_functionality={"Workflow_A.yxmd": [], "Workflow_B.yxmd": ["Unique step"]},
        proposed_strategy="Deterministic proposed strategy.",
        validation_requirements=["Requirement 1"],
        deterministic_metrics=DeterministicMetrics(source_overlap=0.8, transformation_similarity=0.7),
        admissible_recommendations=admissible,
        llm_enrichment_status="DETERMINISTIC_BASELINE",
    )


class TestRationalisationLLMValidation:
    """Test LLM response schema validation, entity boundaries, and deterministic fallback."""

    def test_valid_llm_response_enriched(self):
        """Valid LLM response within admissible bounds is accepted and applied."""
        cand = _build_test_candidate("CONSOLIDATE", ["CONSOLIDATE", "SHARED_LOGIC", "REVIEW"])
        valid_wf_ids = {"wf_a", "wf_b"}
        valid_datasets = {"customer.xlsx", "sales.yxdb"}

        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({
            "recommendation": "CONSOLIDATE",
            "workflow_ids": ["wf_a", "wf_b"],
            "reasoning": "Both workflows process the same customer data with near identical logic.",
            "proposed_strategy": "Combine ingestion pipeline into a shared Alteryx module.",
            "validation_requirements": ["Check pipeline schedules", "Confirm output data marts"],
        })
        mock_generator = MagicMock(client=mock_client)

        result = enrich_candidate_with_llm(cand, mock_generator, valid_wf_ids, valid_datasets)

        assert result.llm_enrichment_status == "ENRICHED"
        assert result.recommendation_type == "CONSOLIDATE"
        assert "Both workflows process the same customer data" in result.reasoning
        # Crucial invariant: Deterministic metrics and opportunity score remain untouched!
        assert result.opportunity_score == 75.0
        assert result.deterministic_metrics.source_overlap == 0.8

    def test_inadmissible_recommendation_rejected(self):
        """If LLM returns a recommendation outside admissible boundary (e.g. RETIRE_CANDIDATE), reject it."""
        # Candidate only allows SHARED_LOGIC or REVIEW
        cand = _build_test_candidate("SHARED_LOGIC", ["SHARED_LOGIC", "REVIEW"])
        valid_wf_ids = {"wf_a", "wf_b"}
        valid_datasets = {"data.csv"}

        mock_client = MagicMock()
        # LLM aggressively tries to declare it a retirement candidate!
        mock_client.generate.return_value = json.dumps({
            "recommendation": "RETIRE_CANDIDATE",
            "workflow_ids": ["wf_a", "wf_b"],
            "reasoning": "Workflow B can be completely retired.",
        })
        mock_generator = MagicMock(client=mock_client)

        result = enrich_candidate_with_llm(cand, mock_generator, valid_wf_ids, valid_datasets)

        # Must fail validation and preserve deterministic recommendation!
        assert result.llm_enrichment_status == "VALIDATION_FAILED"
        assert result.recommendation_type == "SHARED_LOGIC"  # Retains deterministic recommendation!

    def test_hallucinated_workflow_ids_rejected(self):
        """If LLM invents a non-existent workflow ID, reject it and fall back."""
        cand = _build_test_candidate("CONSOLIDATE", ["CONSOLIDATE", "REVIEW"])
        valid_wf_ids = {"wf_a", "wf_b"}
        valid_datasets = {"data.csv"}

        mock_client = MagicMock()
        mock_client.generate.return_value = json.dumps({
            "recommendation": "CONSOLIDATE",
            "workflow_ids": ["wf_a", "wf_invented_999"],  # Hallucinated ID!
            "reasoning": "Consolidate these workflows.",
        })
        mock_generator = MagicMock(client=mock_client)

        result = enrich_candidate_with_llm(cand, mock_generator, valid_wf_ids, valid_datasets)

        assert result.llm_enrichment_status == "VALIDATION_FAILED"
        assert result.recommendation_type == "CONSOLIDATE"

    def test_malformed_json_fallback(self):
        """Malformed JSON or syntax errors must gracefully fall back to deterministic baseline."""
        cand = _build_test_candidate("CONSOLIDATE", ["CONSOLIDATE", "REVIEW"])
        valid_wf_ids = {"wf_a", "wf_b"}

        mock_client = MagicMock()
        mock_client.generate.return_value = "This is not valid JSON at all!"
        mock_generator = MagicMock(client=mock_client)

        result = enrich_candidate_with_llm(cand, mock_generator, valid_wf_ids, set())

        assert result.llm_enrichment_status == "DETERMINISTIC_FALLBACK"
        assert result.reasoning == "Deterministic baseline reasoning."

    def test_client_exception_fallback(self):
        """LLM timeout, network failure, or API exception must gracefully fall back."""
        cand = _build_test_candidate("CONSOLIDATE", ["CONSOLIDATE", "REVIEW"])
        valid_wf_ids = {"wf_a", "wf_b"}

        mock_client = MagicMock()
        mock_client.generate.side_effect = RuntimeError("OpenAI API rate limit exceeded")
        mock_generator = MagicMock(client=mock_client)

        result = enrich_candidate_with_llm(cand, mock_generator, valid_wf_ids, set())

        assert result.llm_enrichment_status == "DETERMINISTIC_FALLBACK"
        assert result.reasoning == "Deterministic baseline reasoning."

    def test_zero_llm_mode(self):
        """When generator is None, returns deterministic baseline immediately."""
        cand = _build_test_candidate("CONSOLIDATE", ["CONSOLIDATE", "REVIEW"])
        result = enrich_candidate_with_llm(cand, None, {"wf_a", "wf_b"}, set())

        assert result.llm_enrichment_status == "DETERMINISTIC_BASELINE"
        assert result.reasoning == "Deterministic baseline reasoning."
