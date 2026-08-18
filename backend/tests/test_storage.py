"""Tests for backend storage service."""

import time
from awa.analysis.workflow_analyzer import analyze_canonical
from backend.app.services.storage import InMemoryStorage


def test_in_memory_storage_lifecycle():
    storage = InMemoryStorage(default_ttl_seconds=10.0)
    result = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    aid = result.analysis_id

    # Save
    saved_id = storage.save(result)
    assert saved_id == aid

    # Retrieve
    retrieved = storage.get(aid)
    assert retrieved is not None
    assert retrieved.analysis_id == aid

    # Delete
    deleted = storage.delete(aid)
    assert deleted is True
    assert storage.get(aid) is None


def test_in_memory_storage_ttl_expiration():
    # 0.1 second TTL
    storage = InMemoryStorage(default_ttl_seconds=0.1)
    result = analyze_canonical("fixtures/basic/simple_filter.yxmd")
    aid = result.analysis_id

    storage.save(result)
    time.sleep(0.2)

    # Retrieval after TTL returns None
    assert storage.get(aid) is None
