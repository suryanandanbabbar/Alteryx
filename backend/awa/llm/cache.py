"""Workflow-scoped deterministic narrative caching with persistent JSON storage."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import (
    NarrativeResult,
    BusinessPurposeResult,
    CriticalityAssessmentResult,
    FactorAssessment,
)

logger = logging.getLogger("awa.llm.cache")

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts" / "llm_cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "llm_cache.json"


def _normalize_facts_for_caching(facts: Any) -> Any:
    """Recursively strip transient file alias fields to ensure identical content produces identical cache keys across renames."""
    if isinstance(facts, dict):
        return {
            k: _normalize_facts_for_caching(v)
            for k, v in facts.items()
            if k not in ("workflow_name", "workflow_filename", "original_filename", "filename")
        }
    if isinstance(facts, list):
        return [_normalize_facts_for_caching(item) for item in facts]
    return facts


def compute_cache_key(
    workflow_id: str,
    scope_key: str,
    prompt_version: str,
    model_name: str,
    facts_payload: dict[str, Any] | None = None,
) -> str:
    """Compute a deterministic hash cache key for a narrative generation request."""
    hasher = hashlib.sha256()
    hasher.update(str(workflow_id).encode("utf-8"))
    hasher.update(b"|")
    hasher.update(str(scope_key).encode("utf-8"))
    hasher.update(b"|")
    hasher.update(str(prompt_version).encode("utf-8"))
    hasher.update(b"|")
    hasher.update(str(model_name).encode("utf-8"))
    if facts_payload:
        normalized = _normalize_facts_for_caching(facts_payload)
        serialized = json.dumps(normalized, sort_keys=True, default=str)
        hasher.update(b"|")
        hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()


def _serialize_cache_entry(value: Any) -> dict[str, Any]:
    """Serialize a cached object to a structured JSON-compatible dictionary."""
    if isinstance(value, BusinessPurposeResult):
        return {
            "schema_type": "BusinessPurposeResult",
            "data": value.to_dict(),
        }
    if isinstance(value, CriticalityAssessmentResult):
        return {
            "schema_type": "CriticalityAssessmentResult",
            "data": value.to_dict(),
        }
    if isinstance(value, NarrativeResult):
        return {
            "schema_type": "NarrativeResult",
            "data": value.to_dict(),
        }
    if isinstance(value, dict):
        return {
            "schema_type": "dict",
            "data": value,
        }
    if isinstance(value, str):
        return {
            "schema_type": "str",
            "data": {"text": value},
        }
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return {
            "schema_type": type(value).__name__,
            "data": value.to_dict(),
        }
    return {
        "schema_type": "raw",
        "data": value,
    }


def _deserialize_cache_entry(entry: dict[str, Any]) -> Any | None:
    """Deserialize a structured dictionary back into the appropriate typed result object."""
    if not isinstance(entry, dict):
        return None

    schema_type = entry.get("schema_type")
    data = entry.get("data")
    if data is None:
        return None

    try:
        if schema_type == "BusinessPurposeResult":
            return BusinessPurposeResult(
                business_purpose=data.get("business_purpose", ""),
                business_function=data.get("business_function", ""),
                business_area_tag=data.get("business_area_tag", ""),
                source=data.get("source", "llm"),
                business_area_taxonomy_version=data.get("business_area_taxonomy_version", "3.0"),
                classification_conflict=data.get("classification_conflict", False),
                classification_evidence=data.get("classification_evidence", []),
                model=data.get("model", ""),
                prompt_version=data.get("prompt_version", "3.1"),
                is_cached=True,
            )

        if schema_type == "CriticalityAssessmentResult":
            factor_assessments = {}
            for k, fa_data in data.get("factor_assessments", {}).items():
                if isinstance(fa_data, dict):
                    factor_assessments[k] = FactorAssessment(
                        dimension=fa_data.get("dimension", k),
                        assessment=fa_data.get("assessment", "NOT_ESTABLISHED"),
                        evidence=fa_data.get("evidence", ""),
                        rationale=fa_data.get("rationale", ""),
                    )
                else:
                    factor_assessments[k] = fa_data

            return CriticalityAssessmentResult(
                criticality_score=float(data.get("criticality_score", 0.0)),
                criticality_level=data.get("criticality_level", "LOW"),
                factor_assessments=factor_assessments,
                criticality_justification=data.get("criticality_justification", ""),
                business_consequence=data.get("business_consequence", ""),
                dependency_impact=data.get("dependency_impact", ""),
                affected_scope=data.get("affected_scope", ""),
                migration_implication=data.get("migration_implication", ""),
                confidence=data.get("confidence", "HIGH"),
                source=data.get("source", "llm"),
                assessment_version=data.get("assessment_version", "2.0"),
                model=data.get("model", ""),
                prompt_version=data.get("prompt_version", "2.0"),
                is_cached=True,
                criticality_factors=data.get("criticality_factors", []),
                deterministic_reference_score=data.get("deterministic_reference_score"),
            )

        if schema_type == "NarrativeResult":
            return NarrativeResult(
                text=data.get("text", ""),
                source=data.get("source", "llm"),
                model=data.get("model", ""),
                prompt_version=data.get("prompt_version", "2.0"),
                is_cached=True,
            )

        if schema_type == "dict":
            return data

        if schema_type == "str":
            return data.get("text", "")

        return data

    except Exception as e:
        logger.warning("Failed to deserialize cache entry with schema_type '%s': %s", schema_type, e)
        return None


class LLMNarrativeCache:
    """Thread-safe, process-safe, two-level persistent cache for LLM generated narratives.
    
    Level 1: In-memory dictionary for instant retrieval.
    Level 2: Persistent JSON file on disk with atomic writes.
    """

    def __init__(
        self,
        file_path: str | Path | None = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        self._store: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

        env_path = os.getenv("AWA_LLM_CACHE_PATH", os.getenv("LLM_CACHE_PATH", "")).strip()
        if file_path is not None:
            self.file_path: Path | None = Path(file_path).resolve()
        elif env_path:
            self.file_path = Path(env_path).resolve()
        else:
            self.file_path = None

        if self.enabled and self.file_path is not None:
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load cached entries from disk with robust error handling and corruption resilience."""
        if self.file_path is None:
            return

        if not self.file_path.exists():
            logger.debug("Cache file %s does not exist yet. Starting with empty cache.", self.file_path)
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.debug("Cache file %s is empty.", self.file_path)
                    return
                raw_data = json.loads(content)

            if not isinstance(raw_data, dict):
                logger.warning(
                    "Cache file %s has invalid structure (expected dict, got %s). Initializing empty cache.",
                    self.file_path,
                    type(raw_data).__name__,
                )
                return

            loaded_count = 0
            for key, entry in raw_data.items():
                if isinstance(entry, dict) and "schema_type" in entry:
                    obj = _deserialize_cache_entry(entry)
                    if obj is not None:
                        self._store[key] = obj
                        loaded_count += 1
                elif isinstance(entry, dict) and "text" in entry:
                    # Backward compatibility with simple serialized NarrativeResult
                    self._store[key] = NarrativeResult(
                        text=entry.get("text", ""),
                        source=entry.get("source", "llm"),
                        model=entry.get("model", ""),
                        prompt_version=entry.get("prompt_version", "2.0"),
                        is_cached=True,
                    )
                    loaded_count += 1
                else:
                    self._store[key] = entry
                    loaded_count += 1

            logger.info("Loaded %d cached LLM results from %s", loaded_count, self.file_path)

        except json.JSONDecodeError as jde:
            logger.warning(
                "Cache file %s is corrupt (JSONDecodeError: %s). Starting with empty cache; file will heal on next write.",
                self.file_path,
                jde,
            )
        except Exception as exc:
            logger.warning(
                "Failed to read cache file %s (%s: %s). Continuing with in-memory cache.",
                self.file_path,
                type(exc).__name__,
                exc,
            )

    def _save_to_disk(self) -> None:
        """Atomically persist in-memory store to disk using a temporary file and replace."""
        if self.file_path is None:
            return

        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            serialized_payload: dict[str, Any] = {}
            for k, v in self._store.items():
                serialized_payload[k] = _serialize_cache_entry(v)

            # Atomic write via NamedTemporaryFile in the same directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.file_path.parent),
                delete=False,
                suffix=".tmp",
            ) as tmp_file:
                json.dump(serialized_payload, tmp_file, indent=2, ensure_ascii=False)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_path = tmp_file.name

            os.replace(tmp_path, str(self.file_path))
            logger.debug("Persisted %d cache entries to %s", len(serialized_payload), self.file_path)

        except Exception as exc:
            logger.warning(
                "Failed to persist cache to %s (%s: %s).",
                self.file_path,
                type(exc).__name__,
                exc,
            )

    def get(self, key: str) -> Any | None:
        """Retrieve cached narrative/result if present."""
        if not self.enabled:
            return None

        with self._lock:
            result = self._store.get(key)
            if result is not None:
                self._hits += 1
                if type(result) is NarrativeResult:
                    return NarrativeResult(
                        text=result.text,
                        source=result.source,
                        model=result.model,
                        prompt_version=result.prompt_version,
                        is_cached=True,
                    )
                if isinstance(result, BusinessPurposeResult):
                    return BusinessPurposeResult(
                        business_purpose=result.business_purpose,
                        business_function=result.business_function,
                        business_area_tag=result.business_area_tag,
                        source=result.source,
                        business_area_taxonomy_version=result.business_area_taxonomy_version,
                        classification_conflict=result.classification_conflict,
                        classification_evidence=list(result.classification_evidence),
                        model=result.model,
                        prompt_version=result.prompt_version,
                        is_cached=True,
                    )
                if isinstance(result, CriticalityAssessmentResult):
                    return CriticalityAssessmentResult(
                        criticality_score=result.criticality_score,
                        criticality_level=result.criticality_level,
                        factor_assessments=dict(result.factor_assessments),
                        criticality_justification=result.criticality_justification,
                        business_consequence=result.business_consequence,
                        dependency_impact=result.dependency_impact,
                        affected_scope=result.affected_scope,
                        migration_implication=result.migration_implication,
                        confidence=result.confidence,
                        source=result.source,
                        assessment_version=result.assessment_version,
                        model=result.model,
                        prompt_version=result.prompt_version,
                        is_cached=True,
                        criticality_factors=list(result.criticality_factors),
                        deterministic_reference_score=result.deterministic_reference_score,
                    )
                if hasattr(result, "is_cached"):
                    result.is_cached = True
                return result

            self._misses += 1
            return None

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Store a generated narrative/result in the cache and persist atomically."""
        if not self.enabled:
            return

        # Refuse to cache explicit fallback results as successful LLM results
        if getattr(value, "source", "") == "deterministic_fallback":
            logger.debug("Refusing to cache deterministic fallback result under key %s", key)
            return

        with self._lock:
            self._store[key] = value
            if persist and self.file_path is not None:
                self._save_to_disk()

    def clear(self) -> None:
        """Clear all cached narratives from memory and disk."""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0
            if self.file_path is not None:
                self._save_to_disk()

    def delete(self, key: str) -> bool:
        """Delete a single key from cache."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                if self.file_path is not None:
                    self._save_to_disk()
                return True
            return False

    def count(self) -> int:
        """Return number of cached items."""
        with self._lock:
            return len(self._store)

    def keys(self) -> list[str]:
        """Return list of all cached keys."""
        with self._lock:
            return list(self._store.keys())

    def stats(self) -> dict[str, Any]:
        """Return operational statistics for monitoring."""
        with self._lock:
            file_exists = self.file_path.exists() if self.file_path is not None else False
            file_size_bytes = self.file_path.stat().st_size if file_exists and self.file_path is not None else 0
            total_requests = self._hits + self._misses
            hit_ratio = (self._hits / total_requests) if total_requests > 0 else 0.0
            return {
                "enabled": self.enabled,
                "entry_count": len(self._store),
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_ratio": hit_ratio,
                "file_path": str(self.file_path) if self.file_path is not None else "in-memory",
                "file_exists": file_exists,
                "file_size_bytes": file_size_bytes,
            }


# Global singleton cache instance
_global_cache: LLMNarrativeCache | None = None
_cache_init_lock = threading.Lock()


def get_global_narrative_cache() -> LLMNarrativeCache:
    """Access the global persistent narrative cache singleton."""
    global _global_cache
    if _global_cache is None:
        with _cache_init_lock:
            if _global_cache is None:
                enabled_str = os.getenv("AWA_LLM_CACHE_ENABLED", os.getenv("LLM_CACHE_ENABLED", "true")).lower()
                is_enabled = enabled_str not in ("false", "0", "no", "off")
                env_path = os.getenv("AWA_LLM_CACHE_PATH", os.getenv("LLM_CACHE_PATH", "")).strip()
                file_path = Path(env_path).resolve() if env_path else DEFAULT_CACHE_FILE.resolve()
                _global_cache = LLMNarrativeCache(file_path=file_path, enabled=is_enabled)
    return _global_cache


def reset_global_narrative_cache(cache: LLMNarrativeCache | None = None) -> None:
    """Reset the global cache instance (useful for test isolation)."""
    global _global_cache
    with _cache_init_lock:
        _global_cache = cache

