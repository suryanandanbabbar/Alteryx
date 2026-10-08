"""Date & validity window licensing criterion."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ..errors import LicenseExpiredError, LicenseInvalidError
from ..verifier import validate_expiry
from .base import CriterionResult

logger = logging.getLogger("awa.licensing.criteria.date")


class DateCriterion:
    """Evaluates license chronology and expiration window."""

    name = "date"

    def __init__(
        self,
        *,
        enabled: bool,
        expires_at: datetime,
        issued_at: datetime | None = None,
        current_time: datetime | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.expires_at = expires_at
        self.issued_at = issued_at
        self.current_time = current_time

    def validate(self) -> CriterionResult:
        """Validate expiration window if enabled."""
        if not self.enabled:
            logger.debug("Date criterion is disabled — skipping expiration check.")
            return CriterionResult(
                name=self.name,
                passed=True,
                enabled=False,
                message="Date criterion disabled.",
            )

        # 1. Chronology check if issued_at is provided
        if self.issued_at is not None:
            if self.issued_at > self.expires_at:
                raise LicenseInvalidError(
                    f"License issued timestamp ({self.issued_at.isoformat()}) "
                    f"cannot be after expiry timestamp ({self.expires_at.isoformat()})."
                )

        # 2. Strict UTC expiry check via existing verifier
        validate_expiry(self.expires_at, current_time=self.current_time)

        return CriterionResult(
            name=self.name,
            passed=True,
            enabled=True,
            message="Date criterion passed.",
        )
