from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr, field_validator, model_validator

from .errors import LicenseInvalidError

EXPECTED_FEATURE_NAMES = (
    "workflow_analysis",
    "portfolio_rationalisation",
    "python_translation",
    "export_reports",
)


class LicenseArtifact(BaseModel):
    """Schema for the signed license document stored in Databricks secret scope.

    Secret: alteryx-license
    Scope: alteryx-licenseArtifacts
    """

    model_config = ConfigDict(extra="forbid")

    license_id: StrictStr
    product: StrictStr
    environment: StrictStr
    issued_at: datetime
    expires_at: datetime
    features: dict[StrictStr, StrictBool]
    signature: StrictStr

    @field_validator("issued_at", "expires_at", mode="before")
    @classmethod
    def validate_utc_iso_timestamp(cls, v: object) -> datetime:
        """Validate that timestamps are ISO-formatted strings with strict UTC timezone."""
        if not isinstance(v, str):
            raise ValueError("Timestamp must be an ISO datetime string.")
        try:
            dt = datetime.fromisoformat(v)
        except Exception as exc:
            raise ValueError(f"Invalid ISO datetime string: {exc}") from exc
        if dt.tzinfo is None:
            raise ValueError(
                "Timestamp must be a timezone-aware UTC timestamp.")
        if dt.utcoffset() != timedelta(0):
            raise ValueError(
                f"Timestamp must be in UTC (+00:00 or Z); non-UTC offset {dt.utcoffset()} is not permitted."
            )
        return dt.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_features(self) -> LicenseArtifact:
        """Validate required feature set."""
        for req_feat in EXPECTED_FEATURE_NAMES:
            if req_feat not in self.features:
                raise ValueError(
                    f"Missing required feature '{req_feat}' in license features.")
            if not isinstance(self.features[req_feat], bool):
                raise ValueError(
                    f"Feature '{req_feat}' must be a strict boolean.")

        return self


class LicenseState:
    """In-memory representation of the active validated license."""

    __slots__ = (
        "is_valid",
        "license_id",
        "product",
        "environment",
        "issued_at",
        "expires_at",
        "features",
    )

    def __init__(
        self,
        *,
        is_valid: bool = False,
        license_id: str = "",
        product: str = "",
        environment: str = "",
        issued_at: datetime | None = None,
        expires_at: datetime | None = None,
        features: dict[str, bool] | None = None,
    ) -> None:
        self.is_valid = is_valid
        self.license_id = license_id
        self.product = product
        self.environment = environment
        self.issued_at = issued_at
        self.expires_at = expires_at
        self.features = dict(features or {})

    @property
    def valid(self) -> bool:
        """Boolean flag indicating whether active license is valid."""
        return self.is_valid

    def has_feature(self, feature_name: str) -> bool:
        """Check if feature is enabled in active license."""
        if not self.is_valid:
            return False
        return self.features.get(feature_name, False)
