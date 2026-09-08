"""Comprehensive test suite for persistent two-level LLM result cache."""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from awa.llm.cache import (
    LLMNarrativeCache,
    compute_cache_key,
    reset_global_narrative_cache,
)
from awa.llm.client import LLMClient
from awa.llm.config import LLMConfig
from awa.llm.generator import LLMNarrativeGenerator
from awa.llm.schemas import (
    BusinessPurposeResult,
    CriticalityAssessmentResult,
    FactorAssessment,
    NarrativeResult,
)
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool
from awa.model.business_summary import WorkflowBusinessSummary


@pytest.fixture
def temp_cache_file(tmp_path):
    """Provide a dedicated temporary cache file path for test isolation."""
    cache_path = tmp_path / "test_llm_cache.json"
    yield cache_path
    if cache_path.exists():
        cache_path.unlink()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with recording capabilities."""
    client = MagicMock(spec=LLMClient)
    client.is_available = True
    client.model_name = "azure-llama-3-3-70b-instruct"
    client.generate.return_value = json.dumps({
        "business_purpose": "Calculates actuarial reserve metrics and loss development factors across policy periods.",
        "business_function": "Actuarial Valuation",
        "business_area_tag": "Actuarial",
    })
    return client


def _make_summary() -> WorkflowBusinessSummary:
    return WorkflowBusinessSummary(
        business_purpose="Calculates actuarial reserve metrics.",
        one_line_purpose="Actuarial valuation pipeline.",
        why_it_matters="Ensures solvency and reserve adequacy.",
    )


class TestLLMPersistentCache:
    """Test suite for Level 1 (RAM) + Level 2 (JSON) persistent LLM caching."""

    def test_01_empty_cache_miss_calls_llm_and_stores_result(self, temp_cache_file, mock_llm_client):
        """Scenario 1: Initial call with empty cache results in MISS, LLM call, and persistent disk write."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)

        workflow = Workflow(
            metadata=WorkflowMetadata(name="WF01", version="2023.1"),
            content_hash="abc123hash",
        )
        summary = _make_summary()

        # Execute generation
        result = generator.generate_business_purpose(workflow, summary, workflow_id="abc123hash")

        assert result is not None
        assert result.source == "llm"
        assert result.business_area_tag == "Actuarial"
        assert mock_llm_client.generate.call_count == 1

        # Check in-memory count
        assert cache.count() == 1

        # Check persistent JSON file exists and contains the serialized result
        assert temp_cache_file.exists()
        with open(temp_cache_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        assert len(disk_data) == 1
        entry_key = list(disk_data.keys())[0]
        assert disk_data[entry_key]["schema_type"] == "BusinessPurposeResult"
        assert disk_data[entry_key]["data"]["business_area_tag"] == "Actuarial"

    def test_02_repeated_request_returns_fast_cache_hit_zero_llm_calls(self, temp_cache_file, mock_llm_client):
        """Scenario 2: Subsequent call with identical inputs results in instant cache HIT with 0 external LLM calls."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)

        workflow = Workflow(
            metadata=WorkflowMetadata(name="WF01", version="2023.1"),
            content_hash="abc123hash",
        )

        # Run 1: Store
        res1 = generator.generate_business_purpose(workflow, _make_summary(), workflow_id="abc123hash")
        assert mock_llm_client.generate.call_count == 1

        # Run 2: HIT
        res2 = generator.generate_business_purpose(workflow, _make_summary(), workflow_id="abc123hash")
        assert mock_llm_client.generate.call_count == 1  # ZERO additional LLM calls
        assert res2.is_cached is True
        assert res2.business_purpose == res1.business_purpose
        assert res2.business_area_tag == res1.business_area_tag

        # Create a brand new cache instance pointing to the same file (simulating new server process)
        cache_new_process = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator_new = LLMNarrativeGenerator(client=mock_llm_client, cache=cache_new_process)

        res3 = generator_new.generate_business_purpose(workflow, _make_summary(), workflow_id="abc123hash")
        assert mock_llm_client.generate.call_count == 1  # Still zero extra calls
        assert res3.is_cached is True
        assert res3.business_area_tag == "Actuarial"

    def test_03_renamed_workflow_with_identical_content_produces_cache_hit(self, temp_cache_file, mock_llm_client):
        """Scenario 3: Renamed workflow with identical content hash produces cache HIT with zero LLM calls."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)

        # Upload 1: Original file
        wf_original = Workflow(
            metadata=WorkflowMetadata(name="BillingPipeline_v1.yxmd", version="2023.1"),
            content_hash="identical_content_sha256_hash",
        )
        res1 = generator.generate_business_purpose(wf_original, _make_summary())
        assert mock_llm_client.generate.call_count == 1

        # Upload 2: Renamed file with identical content hash
        wf_renamed = Workflow(
            metadata=WorkflowMetadata(name="Copy_Of_BillingPipeline_Final.yxmd", version="2023.1"),
            content_hash="identical_content_sha256_hash",
        )
        res2 = generator.generate_business_purpose(wf_renamed, _make_summary())

        # Should be a cache HIT because content hash is identical
        assert mock_llm_client.generate.call_count == 1
        assert res2.is_cached is True
        assert res2.business_purpose == res1.business_purpose

    def test_04_modified_workflow_content_triggers_cache_miss(self, temp_cache_file, mock_llm_client):
        """Scenario 4: Modifying workflow content changes content hash, triggering a cache MISS and re-run."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)

        wf_v1 = Workflow(
            metadata=WorkflowMetadata(name="WF.yxmd", version="2023.1"),
            content_hash="hash_v1",
        )
        generator.generate_business_purpose(wf_v1, _make_summary())
        assert mock_llm_client.generate.call_count == 1

        # Workflow modified -> new content hash
        wf_v2 = Workflow(
            metadata=WorkflowMetadata(name="WF.yxmd", version="2023.1"),
            content_hash="hash_v2_modified",
        )
        generator.generate_business_purpose(wf_v2, _make_summary())
        assert mock_llm_client.generate.call_count == 2
        assert cache.count() == 2

    def test_05_prompt_version_change_invalidates_cache(self, temp_cache_file, mock_llm_client):
        """Scenario 5: Changing prompt version produces a new cache key resulting in a cache MISS."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)

        wf = Workflow(
            metadata=WorkflowMetadata(name="WF.yxmd", version="2023.1"),
            content_hash="hash_stable",
        )
        generator.generate_business_purpose(wf, _make_summary())
        assert mock_llm_client.generate.call_count == 1

        # Simulate prompt version update
        with patch("awa.llm.generator.WORKFLOW_PURPOSE_PROMPT_VERSION", "9.9"):
            generator.generate_business_purpose(wf, _make_summary())
            assert mock_llm_client.generate.call_count == 2

    def test_06_llm_failure_does_not_cache_fallback(self, temp_cache_file):
        """Scenario 6: When LLM fails with exception, deterministic fallback is returned and NOT cached as successful."""
        failing_client = MagicMock(spec=LLMClient)
        failing_client.is_available = True
        failing_client.model_name = "test-model"
        failing_client.generate.side_effect = RuntimeError("Azure 503 Service Unavailable")

        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        generator = LLMNarrativeGenerator(client=failing_client, cache=cache)

        wf = Workflow(
            metadata=WorkflowMetadata(name="WF.yxmd", version="2023.1"),
            content_hash="fail_hash",
        )
        res = generator.generate_business_purpose(wf, _make_summary())
        assert res.source == "deterministic_fallback"
        # The failed/fallback result must NOT be cached in persistent store
        assert cache.count() == 0

        # Also verify cache.set directly rejects fallback objects
        cache.set("dummy_key", res)
        assert cache.count() == 0

    def test_07_corrupted_json_file_heals_gracefully(self, temp_cache_file, mock_llm_client):
        """Scenario 7: Corrupted JSON cache file is caught safely, logs warning, and heals on next write."""
        # Write corrupted JSON to cache file
        with open(temp_cache_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json truncated here ...")

        # Loading cache should not raise an exception
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        assert cache.count() == 0

        # Now perform a valid write
        generator = LLMNarrativeGenerator(client=mock_llm_client, cache=cache)
        wf = Workflow(
            metadata=WorkflowMetadata(name="WF.yxmd", version="2023.1"),
            content_hash="heal_hash",
        )
        generator.generate_business_purpose(wf, _make_summary())

        assert cache.count() == 1
        # File on disk should now be valid JSON
        with open(temp_cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1

    def test_08_schema_invalid_entry_returns_miss(self, temp_cache_file, mock_llm_client):
        """Scenario 8: Cache entries with missing or corrupted fields are rejected during get()."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        # Store invalid raw entry manually
        cache._store["corrupt_key"] = None
        assert cache.get("corrupt_key") is None

        # Store entry that throws on deserialize
        cache._store["malformed_entry"] = MagicMock(side_effect=Exception("corrupt object"))
        assert cache.get("nonexistent_key") is None

    def test_09_atomic_writes_and_concurrent_safety(self, temp_cache_file):
        """Scenario 9: Concurrent multi-threaded writes persist atomically without race conditions."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)

        def worker(worker_id: int):
            for i in range(10):
                res = NarrativeResult(
                    text=f"Narrative from worker {worker_id} item {i}",
                    source="llm",
                    model="test-model",
                    prompt_version="2.0",
                )
                cache.set(f"key_{worker_id}_{i}", res)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cache.count() == 50

        # Reload from disk into a fresh instance
        reloaded_cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        assert reloaded_cache.count() == 50

    def test_10_cache_stats_and_clear(self, temp_cache_file):
        """Scenario 10: Cache inspection, hit/miss tracking, and clearing functions work accurately."""
        cache = LLMNarrativeCache(file_path=temp_cache_file, enabled=True)
        cache.set(
            "k1",
            NarrativeResult(text="Text 1", source="llm", model="m", prompt_version="2.0"),
        )

        # 1 hit, 1 miss
        assert cache.get("k1") is not None
        assert cache.get("k2_nonexistent") is None

        stats = cache.stats()
        assert stats["enabled"] is True
        assert stats["entry_count"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_ratio"] == 0.5
        assert stats["file_exists"] is True

        # Clear
        cache.clear()
        assert cache.count() == 0
        assert len(cache.keys()) == 0
