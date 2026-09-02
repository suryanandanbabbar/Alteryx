"""Workflow-scoped deterministic narrative caching."""

from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from .schemas import NarrativeResult


def compute_cache_key(
    workflow_id: str,
    scope_key: str,
    prompt_version: str,
    model_name: str,
    facts_payload: dict[str, Any] | None = None,
) -> str:
    """Compute a deterministic hash cache key for a narrative generation request."""
    hasher = hashlib.sha256()
    hasher.update(workflow_id.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(scope_key.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(prompt_version.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(model_name.encode("utf-8"))
    if facts_payload:
        serialized = json.dumps(facts_payload, sort_keys=True)
        hasher.update(b"|")
        hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


class LLMNarrativeCache:
    """Thread-safe in-memory cache for LLM generated narratives."""

    def __init__(self) -> None:
        self._store: dict[str, NarrativeResult] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """Retrieve cached narrative if present."""
        with self._lock:
            result = self._store.get(key)
            if result is not None:
                if type(result) is NarrativeResult:
                    return NarrativeResult(
                        text=result.text,
                        source=result.source,
                        model=result.model,
                        prompt_version=result.prompt_version,
                        is_cached=True,
                    )
                if hasattr(result, "is_cached"):
                    result.is_cached = True
                return result
            return None

    def set(self, key: str, narrative: NarrativeResult) -> None:
        """Store a generated narrative in the cache."""
        with self._lock:
            self._store[key] = narrative

    def clear(self) -> None:
        """Clear all cached narratives."""
        with self._lock:
            self._store.clear()

    def count(self) -> int:
        """Return number of cached items."""
        with self._lock:
            return len(self._store)


# Global singleton cache instance
_global_cache = LLMNarrativeCache()


def get_global_narrative_cache() -> LLMNarrativeCache:
    """Access the global narrative cache."""
    return _global_cache
