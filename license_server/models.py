"""Data models for the License API Server.

Defines the authoritative client/server protocol models and internal repository records.
Wire contract is strictly compatible with ``backend.app.licensing.models``.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    """Authoritative license statuses supported by the system."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    INVALID = "invalid"


class LicenseValidationRequest(BaseModel):
    """Validation request received at ``POST /v1/license/validate``."""

    license_id: str
    product: str
    client_instance_id: str
    environment: str = "production"
    request_id: str


class LicenseValidationResponse(BaseModel):
    """Authoritative validation response returned to the client.

    The ``signature`` field contains the base64-encoded Ed25519 signature
    computed over the canonical JSON representation of all other fields.
    """

    license_id: str
    product: str
    environment: str = "production"
    client_instance_id: str
    request_id: str
    status: LicenseStatus
    lease_expires_at: datetime
    server_time: datetime
    features: dict[str, bool] = Field(default_factory=dict)
    message: str = ""
    signature: str = ""


class LicenseRecord(BaseModel):
    """Internal license record maintained by the repository."""

    license_id: str
    product: str = "alteryx-etl"
    environment: str = "production"
    status: LicenseStatus = LicenseStatus.ACTIVE
    expires_at: datetime | None = None
    features: dict[str, bool] = Field(default_factory=dict)
