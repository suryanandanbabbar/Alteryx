"""Generic usage data source abstraction for universal licensing enforcement.

The licensing package does not count, track, monitor, or record usage metrics.
Applications or external datastores are authoritative for current cumulative usage.
The licensing SDK simply queries this abstraction at startup and verifies limits.
"""

from __future__ import annotations

import logging
from typing import Callable, Protocol, runtime_checkable

logger = logging.getLogger("awa.licensing.usage_source")


@runtime_checkable
class UsageDataSource(Protocol):
    """Protocol for reading cumulative usage metrics (volume, tokens, etc.)."""

    def get_current_usage(self) -> int:
        """Retrieve current cumulative usage metric as an integer.

        Returns:
            Non-negative integer representing current cumulative usage.

        Raises:
            Exception: If the underlying source cannot be queried or is unavailable.
        """
        ...


class InMemoryUsageDataSource:
    """In-memory usage data source for testing and local development."""

    def __init__(self, usage: int = 0) -> None:
        self._usage = int(usage)

    def set_usage(self, usage: int) -> None:
        """Set current usage value."""
        self._usage = int(usage)

    def get_current_usage(self) -> int:
        """Return the configured in-memory usage value."""
        return self._usage


class CallableUsageDataSource:
    """Usage data source wrapping an arbitrary zero-argument callable."""

    def __init__(self, fetch_fn: Callable[[], int]) -> None:
        self._fetch_fn = fetch_fn

    def get_current_usage(self) -> int:
        """Invoke wrapped callable and return integer result."""
        result = self._fetch_fn()
        return int(result)
