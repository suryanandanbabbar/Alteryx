"""Developer Configuration Model & Service for Universal Modular Licensing.

Provides EXL developers with authoritative configuration management,
validation across all 6 sections (Identity, Artifact Secret, Enforcement Criteria,
Date, Volume, Token Usage), and unsigned artifact generation for Ed25519 signing.

Package-local configuration source:
    backend/app/licensing/developer_config.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .errors import LicenseConfigurationError
from .models import EXPECTED_FEATURE_NAMES, DatePolicy, LicensePolicy, TokenUsagePolicy, VolumePolicy

logger = logging.getLogger("awa.licensing.developer_config")

# Authoritative package-relative path to developer_config.json
DEFAULT_DEVELOPER_CONFIG_PATH = Path(__file__).resolve().parent / "developer_config.json"


class IdentitySection(BaseModel):
    """Section 1: License & Application Identity."""

    model_config = ConfigDict(extra="forbid")

    license_id: str
    product: str
    environment: str

    @field_validator("license_id", "product", "environment")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty.")
        return v.strip()


class ArtifactSecretSection(BaseModel):
    """Section 2: Artifact Secret Coordinates."""

    model_config = ConfigDict(extra="forbid")

    secret_scope: str
    secret_name: str

    @field_validator("secret_scope", "secret_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty.")
        return v.strip()


class EnforcementCriteriaSection(BaseModel):
    """Section 3: Criteria Activation Flags (strictly 0 or 1)."""

    model_config = ConfigDict(extra="forbid")

    date_enabled: int = 1
    volume_enabled: int = 0
    token_usage_enabled: int = 0

    @field_validator("date_enabled", "volume_enabled", "token_usage_enabled")
    @classmethod
    def validate_flag(cls, v: int) -> int:
        if type(v) is not int or v not in (0, 1):
            raise ValueError("Criteria flag must be strictly 0 or 1.")
        return v

    @model_validator(mode="after")
    def validate_not_all_zero(self) -> EnforcementCriteriaSection:
        if self.date_enabled == 0 and self.volume_enabled == 0 and self.token_usage_enabled == 0:
            raise ValueError("At least one criteria flag must be 1. Combination 0/0/0 is invalid.")
        return self


class DateCriteriaSection(BaseModel):
    """Section 4: Date Validity Window."""

    model_config = ConfigDict(extra="forbid")

    issued_date: str
    expiry_date: str

    @field_validator("issued_date", "expiry_date")
    @classmethod
    def validate_iso_date(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Date string cannot be empty.")
        v_clean = v.strip()
        # Accept YYYY-MM-DD or full ISO
        try:
            if len(v_clean) == 10:
                dt = datetime.strptime(v_clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                dt = datetime.fromisoformat(v_clean)
            if dt.tzinfo is None:
                raise ValueError("Date must be UTC timezone-aware.")
        except Exception as exc:
            raise ValueError(f"Invalid ISO date/timestamp: {exc}") from exc
        return v_clean


class UsageSourceConfig(BaseModel):
    """Declarative usage source specification."""

    model_config = ConfigDict(extra="forbid")

    type: str = "custom"
    identifier: str = ""


class VolumeCriteriaSection(BaseModel):
    """Section 5: Cumulative Volume Limit."""

    model_config = ConfigDict(extra="forbid")

    volume_limit: int = 0
    usage_source: UsageSourceConfig = Field(
        default_factory=lambda: UsageSourceConfig(identifier="volume_usage")
    )

    @field_validator("volume_limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if type(v) is not int or v < 0:
            raise ValueError("Volume limit must be a non-negative integer.")
        return v


class TokenUsageCriteriaSection(BaseModel):
    """Section 6: Cumulative Token Usage Limit."""

    model_config = ConfigDict(extra="forbid")

    token_usage_limit: int = 0
    usage_source: UsageSourceConfig = Field(
        default_factory=lambda: UsageSourceConfig(identifier="token_usage")
    )

    @field_validator("token_usage_limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if type(v) is not int or v < 0:
            raise ValueError("Token usage limit must be a non-negative integer.")
        return v


class DeveloperLicenseConfig(BaseModel):
    """Authoritative developer configuration spanning all 6 sections."""

    model_config = ConfigDict(extra="forbid")

    identity: IdentitySection
    artifact_secret: ArtifactSecretSection
    enforcement: EnforcementCriteriaSection = Field(default_factory=EnforcementCriteriaSection)
    date: DateCriteriaSection
    volume: VolumeCriteriaSection = Field(default_factory=VolumeCriteriaSection)
    token_usage: TokenUsageCriteriaSection = Field(default_factory=TokenUsageCriteriaSection)
    features: dict[str, bool] = Field(
        default_factory=lambda: {feat: True for feat in EXPECTED_FEATURE_NAMES}
    )

    @model_validator(mode="after")
    def validate_chronology_if_date_enabled(self) -> DeveloperLicenseConfig:
        if self.enforcement.date_enabled == 1:
            try:
                iss_str = self.date.issued_date
                exp_str = self.date.expiry_date
                iss_dt = datetime.strptime(iss_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if len(iss_str) == 10 else datetime.fromisoformat(iss_str)
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if len(exp_str) == 10 else datetime.fromisoformat(exp_str)
                if iss_dt > exp_dt:
                    raise ValueError(f"Issued date ({iss_str}) cannot be after expiry date ({exp_str}).")
            except Exception as exc:
                raise ValueError(f"Date validation error: {exc}") from exc
        return self

    def generate_unsigned_artifact_payload(self) -> dict[str, Any]:
        """Construct the unsigned canonical JSON payload ready for Ed25519 signing.

        Produces a dictionary containing:
        - identity fields (license_id, product, environment)
        - issued_at and expires_at formatted in strict UTC ISO
        - feature flags dictionary
        - signed policy object for multi-criteria enforcement (date, volume, token_usage)
        """
        iss_str = self.date.issued_date
        exp_str = self.date.expiry_date
        iss_dt = datetime.strptime(iss_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if len(iss_str) == 10 else datetime.fromisoformat(iss_str)
        exp_dt = datetime.strptime(exp_str, "%Y-%m-%d").replace(tzinfo=timezone.utc) if len(exp_str) == 10 else datetime.fromisoformat(exp_str)

        # Canonical ISO format YYYY-MM-DDTHH:MM:SSZ
        iss_formatted = iss_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        exp_formatted = exp_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        policy_dict = {
            "date": {
                "enabled": bool(self.enforcement.date_enabled),
            },
            "volume": {
                "enabled": bool(self.enforcement.volume_enabled),
                "limit": self.volume.volume_limit,
            },
            "token_usage": {
                "enabled": bool(self.enforcement.token_usage_enabled),
                "limit": self.token_usage.token_usage_limit,
            },
        }

        return {
            "license_id": self.identity.license_id,
            "product": self.identity.product,
            "environment": self.identity.environment,
            "issued_at": iss_formatted,
            "expires_at": exp_formatted,
            "features": dict(self.features),
            "policy": policy_dict,
        }

    def save_to_file(self, file_path: Path | None = None) -> None:
        """Persist developer configuration to disk."""
        target_path = file_path or DEFAULT_DEVELOPER_CONFIG_PATH
        data = self.model_dump()
        target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, file_path: Path | None = None) -> DeveloperLicenseConfig:
        """Load developer configuration from disk."""
        target_path = file_path or DEFAULT_DEVELOPER_CONFIG_PATH
        if not target_path.exists():
            raise LicenseConfigurationError(
                f"Developer license configuration file not found at: {target_path}"
            )
        try:
            data = json.loads(target_path.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        except Exception as exc:
            raise LicenseConfigurationError(
                f"Failed to load developer license config from {target_path}: {exc}"
            ) from exc
