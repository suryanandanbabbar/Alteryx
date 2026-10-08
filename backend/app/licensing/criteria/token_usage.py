"""Token usage licensing criterion."""

from __future__ import annotations

import logging
from typing import Any

from ..errors import LicenseInvalidError, LicenseLimitExceededError
from ..usage_source import UsageDataSource
from .base import CriterionResult

logger = logging.getLogger("awa.licensing.criteria.token_usage")


class TokenUsageCriterion:
    """Evaluates cumulative token usage against the configured token limit."""

    name = "token_usage"

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
        """Validate cumulative token usage if enabled."""
        if not self.enabled:
            logger.debug("Token usage criterion is disabled — skipping token usage check.")
            return CriterionResult(
                name=self.name,
                passed=True,
                enabled=False,
                message="Token usage criterion disabled.",
            )

        # 1. Validate configured limit
        if not isinstance(self.limit, int) or isinstance(self.limit, bool) or self.limit < 0:
            raise LicenseInvalidError(
                f"Configured token limit must be a non-negative integer, got {self.limit!r}."
            )

        # 2. Validate usage source presence
        if self.usage_source is None:
            raise LicenseInvalidError(
                "Token usage source is required when token enforcement is enabled."
            )

        # 3. Retrieve current cumulative tokens (fail-closed on source error)
        try:
            current = self.usage_source.get_current_usage()
        except Exception as exc:
            logger.error("Token usage source query failed: %s", exc)
            raise LicenseInvalidError(
                f"Failed to retrieve current token usage from source: {exc}"
            ) from exc

        # 4. Validate source returned a non-negative integer
        if not isinstance(current, int) or isinstance(current, bool) or current < 0:
            raise LicenseInvalidError(
                f"Token usage source returned invalid usage: {current!r}. Expected non-negative integer."
            )

        # 5. Evaluate boundary condition: current >= limit triggers failure
        if current >= self.limit:
            logger.warning(
                "Token usage limit exceeded: current=%d limit=%d (license_id=%s)",
                current,
                self.limit,
                self.license_id,
            )
            raise LicenseLimitExceededError(
                criterion="token_usage",
                current=current,
                limit=self.limit,
                license_id=self.license_id,
                message=f"Token usage license limit reached: {current}/{self.limit}.",
            )

        return CriterionResult(
            name=self.name,
            passed=True,
            enabled=True,
            current=current,
            limit=self.limit,
            message="Token usage criterion passed.",
        )
