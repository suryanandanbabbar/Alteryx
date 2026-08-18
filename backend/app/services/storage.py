"""Storage service abstraction and in-memory TTL implementation."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

from awa.model.analysis_result import CanonicalAnalysisResult


@dataclass
class StorageEntry:
    result: CanonicalAnalysisResult
    created_at: float
    ttl_seconds: float


class StorageService(ABC):
    """Abstract interface for analysis result persistence."""

    @abstractmethod
    def save(self, result: CanonicalAnalysisResult, ttl_seconds: float = 3600.0) -> str:
        """Store an analysis result and return its analysis_id."""
        ...

    @abstractmethod
    def get(self, analysis_id: str) -> CanonicalAnalysisResult | None:
        """Retrieve an analysis result by analysis_id."""
        ...

    @abstractmethod
    def delete(self, analysis_id: str) -> bool:
        """Remove an analysis result by analysis_id."""
        ...

    @abstractmethod
    def cleanup(self) -> int:
        """Purge expired entries, returning the number of cleaned items."""
        ...


class InMemoryStorage(StorageService):
    """In-memory dictionary storage with TTL.

    Note: Ephemeral. Entries are lost upon application restart.
    """

    def __init__(self, default_ttl_seconds: float = 3600.0):
        self._store: Dict[str, StorageEntry] = {}
        self.default_ttl = default_ttl_seconds

    def save(self, result: CanonicalAnalysisResult, ttl_seconds: float | None = None) -> str:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        entry = StorageEntry(
            result=result,
            created_at=time.time(),
            ttl_seconds=ttl,
        )
        self._store[result.analysis_id] = entry
        return result.analysis_id

    def get(self, analysis_id: str) -> CanonicalAnalysisResult | None:
        entry = self._store.get(analysis_id)
        if entry is None:
            return None
        # Check TTL
        if time.time() - entry.created_at > entry.ttl_seconds:
            self._store.pop(analysis_id, None)
            return None
        return entry.result

    def delete(self, analysis_id: str) -> bool:
        return self._store.pop(analysis_id, None) is not None

    def cleanup(self) -> int:
        now = time.time()
        expired = [
            aid for aid, entry in self._store.items()
            if now - entry.created_at > entry.ttl_seconds
        ]
        for aid in expired:
            self._store.pop(aid, None)
        return len(expired)


# Global storage instance
_global_storage = InMemoryStorage()


def get_storage() -> StorageService:
    """Get the active storage service instance."""
    return _global_storage
