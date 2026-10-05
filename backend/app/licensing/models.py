"""Data models for the Azure License API contract and in-memory lease state.

These models define the wire-format contract between the client application
and the Azure License API.  Changing these models is safe as long as both
sides are updated together.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    """Possible license statuses returned by the Azure License API."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    INVALID = "invalid"


class LicenseValidationRequest(BaseModel):
    """Request payload sent to ``POST {api_url}/v1/license/validate``."""

    license_id: str
    product: str
    client_instance_id: str
    environment: str = "production"
    request_id: str


class LicenseValidationResponse(BaseModel):
    """Response payload from the Azure License API.

    The ``signature`` field contains a base64-encoded Ed25519 signature
    covering the canonical JSON representation of all other fields, including
    the bound ``request_id``, ``product``, and ``environment``.
    """

    license_id: str
    product: str
    environment: str = "production"
    client_instance_id: str | None = None
    request_id: str
    status: LicenseStatus
    lease_expires_at: datetime
    server_time: datetime
    features: dict[str, bool] = Field(default_factory=dict)
    message: str = ""
    signature: str


# ── In-memory lease state ────────────────────────────────────────────


class LeaseState:
    """In-memory lease state tracking.

    NOT persisted to disk to prevent local tampering.
    Uses monotonic elapsed time to track offline grace duration during
    the process lifetime, preventing wall-clock manipulation.
    """

    __slots__ = (
        "valid",
        "status",
        "lease_expires_at",
        "server_time",
        "last_successful_validation",
        "last_attempt",
        "consecutive_failures",
        "last_successful_monotonic",
        "outage_start_monotonic",
    )

    def __init__(self) -> None:
        self.valid: bool = False
        self.status: LicenseStatus | None = None
        self.lease_expires_at: datetime | None = None
        self.server_time: datetime | None = None
        self.last_successful_validation: datetime | None = None
        self.last_attempt: datetime | None = None
        self.consecutive_failures: int = 0
        self.last_successful_monotonic: float | None = None
        self.outage_start_monotonic: float | None = None

    def update_from_response(self, response: LicenseValidationResponse) -> None:
        """Update state from a successfully verified and bound API response."""
        self.valid = response.status == LicenseStatus.ACTIVE
        self.status = response.status
        self.lease_expires_at = response.lease_expires_at
        self.server_time = response.server_time
        self.last_successful_validation = response.server_time
        self.last_attempt = response.server_time
        self.consecutive_failures = 0
        self.last_successful_monotonic = time.monotonic()
        self.outage_start_monotonic = None

    def record_failure(self) -> None:
        """Record a failed validation attempt (network error).

        Starts tracking monotonic outage duration if an active lease exists.
        """
        self.last_attempt = datetime.now(timezone.utc)
        self.consecutive_failures += 1
        if self.outage_start_monotonic is None:
            self.outage_start_monotonic = time.monotonic()

    def is_within_grace(self, grace_seconds: int) -> bool:
        """Check whether the current time is still within the grace period.

        Security Enforcement:
        1. If no prior valid lease was obtained, returns False (startup fails closed).
        2. During a running process outage, monotonic elapsed time is checked:
           monotonic time cannot be altered by local wall-clock changes.
        3. Wall-clock timestamp against server-issued lease_expires_at + grace_seconds
           is also enforced as an additional upper bound.
        """
        if (
            self.lease_expires_at is None
            or self.last_successful_validation is None
            or not self.valid
        ):
            return False

        # Monotonic elapsed time check during current process outage
        if self.outage_start_monotonic is not None:
            elapsed_outage = time.monotonic() - self.outage_start_monotonic
            if elapsed_outage > grace_seconds:
                return False

        # Elapsed since last successful validation check
        if self.last_successful_monotonic is not None:
            elapsed_since_success = time.monotonic() - self.last_successful_monotonic
            if elapsed_since_success > grace_seconds:
                return False

        # Wall-clock upper bound check against server-issued expiry
        now_utc = datetime.now(timezone.utc)
        lease_exp = self.lease_expires_at
        if lease_exp.tzinfo is None:
            lease_exp = lease_exp.replace(tzinfo=timezone.utc)

        grace_deadline = lease_exp + timedelta(seconds=grace_seconds)
        return now_utc < grace_deadline
