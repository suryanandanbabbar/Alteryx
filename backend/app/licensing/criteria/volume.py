"""Volume licensing criterion."""

from __future__ import annotations

import logging
from typing import Any

from ..errors import LicenseInvalidError, LicenseLimitExceededError
from ..usage_source import UsageDataSource
from .base import CriterionResult

logger = logging.getLogger("awa.licensing.criteria.volume")


class VolumeCriterion:
    """Evaluates cumulative volume against the configured volume limit."""

    name = "volume"

    def __init__(
        self,
        *,
        enabled: bool,
        limit: int = 0,
        usage_source: UsageDataSource | None = None,
        license_id: str = "",
    ) -> None:
        self.enabled = bool(enabled)
        self.limit = limit
        self.usage_source = usage_source
        self.license_id = license_id

    def validate(self) -> CriterionResult:
        """Validate cumulative volume usage if enabled."""
        if not self.enabled:
            logger.debug("Volume criterion is disabled — skipping volume check.")
            return CriterionResult(
                name=self.name,
                passed=True,
                enabled=False,
                message="Volume criterion disabled.",
            )

        # 1. Validate configured limit
        if not isinstance(self.limit, int) or isinstance(self.limit, bool) or self.limit < 0:
            raise LicenseInvalidError(
                f"Configured volume limit must be a non-negative integer, got {self.limit!r}."
            )

        # 2. Validate usage source presence
        if self.usage_source is None:
            raise LicenseInvalidError(
                "Volume usage source is required when volume enforcement is enabled."
            )

        # 3. Retrieve current cumulative volume (fail-closed on source error)
        try:
            current = self.usage_source.get_current_usage()
        except Exception as exc:
            logger.error("Volume usage source query failed: %s", exc)
            raise LicenseInvalidError(
                f"Failed to retrieve current volume usage from source: {exc}"
            ) from exc

        # 4. Validate source returned a non-negative integer
        if not isinstance(current, int) or isinstance(current, bool) or current < 0:
            raise LicenseInvalidError(
                f"Volume usage source returned invalid usage: {current!r}. Expected non-negative integer."
            )

        # 5. Evaluate boundary condition: current >= limit triggers failure
        if current >= self.limit:
            logger.warning(
                "Volume limit exceeded: current=%d limit=%d (license_id=%s)",
                current,
                self.limit,
                self.license_id,
            )
            raise LicenseLimitExceededError(
                criterion="volume",
                current=current,
                limit=self.limit,
                license_id=self.license_id,
                message=f"Volume license limit reached: {current}/{self.limit}.",
            )

        return CriterionResult(
            name=self.name,
            passed=True,
            enabled=True,
            current=current,
            limit=self.limit,
            message="Volume criterion passed.",
        )
