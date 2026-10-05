"""Server configuration loaded from environment variables.

SECURITY NOTICE:
The Ed25519 private signing key is NEVER loaded from environment variables
or files on disk. The private key is retrieved exclusively from Azure Key Vault
via Managed Identity at runtime.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

from .errors import LicenseConfigurationError

logger = logging.getLogger("license_server.config")

_DEFAULT_SECRET_NAME = "alteryx-license-private-key"
_DEFAULT_LEASE_SECONDS = 86_400


@dataclass(frozen=True)
class ServerConfig:
    """Immutable configuration for the License Server."""

    key_vault_url: str = ""
    private_key_secret_name: str = _DEFAULT_SECRET_NAME
    default_product: str = "alteryx-etl"
    default_environment: str = "production"
    default_license_id: str = ""
    default_status: str = "active"
    default_expiry: datetime | None = None
    lease_seconds: int = _DEFAULT_LEASE_SECONDS
    default_features: dict[str, bool] = field(default_factory=dict)
    api_client_secret: str = ""

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Construct configuration from environment variables with controlled error handling."""
        # Parse features JSON if provided
        features_raw = os.getenv("ALTERYX_LICENSE_FEATURES", "").strip()
        features: dict[str, bool] = {}
        if features_raw:
            try:
                parsed = json.loads(features_raw)
                if not isinstance(parsed, dict):
                    raise ValueError("Must be a JSON object")
                features = parsed
            except Exception as exc:
                raise LicenseConfigurationError(
                    "ALTERYX_LICENSE_FEATURES must be a valid JSON object."
                ) from exc

        # Parse expiry datetime if provided
        expiry_raw = os.getenv("ALTERYX_LICENSE_EXPIRY", "").strip()
        expiry: datetime | None = None
        if expiry_raw:
            try:
                expiry = datetime.fromisoformat(expiry_raw)
            except Exception as exc:
                raise LicenseConfigurationError(
                    "ALTERYX_LICENSE_EXPIRY must be a valid ISO 8601 datetime."
                ) from exc

        # Parse lease seconds
        lease_raw = os.getenv(
            "ALTERYX_LICENSE_LEASE_SECONDS", str(_DEFAULT_LEASE_SECONDS)
        ).strip()
        try:
            lease_seconds = int(lease_raw)
            if lease_seconds <= 0:
                raise ValueError("Must be positive")
        except ValueError as exc:
            raise LicenseConfigurationError(
                "ALTERYX_LICENSE_LEASE_SECONDS must be a positive integer."
            ) from exc

        return cls(
            key_vault_url=os.getenv("AZURE_KEY_VAULT_URL", "").strip(),
            private_key_secret_name=os.getenv(
                "AZURE_LICENSE_PRIVATE_KEY_SECRET_NAME", _DEFAULT_SECRET_NAME
            ).strip()
            or _DEFAULT_SECRET_NAME,
            default_product=os.getenv("ALTERYX_LICENSE_PRODUCT", "alteryx-etl").strip(),
            default_environment=os.getenv(
                "ALTERYX_LICENSE_ENVIRONMENT", "production"
            ).strip(),
            default_license_id=os.getenv("ALTERYX_LICENSE_ID", "").strip(),
            default_status=os.getenv("ALTERYX_LICENSE_STATUS", "active").strip().lower(),
            default_expiry=expiry,
            lease_seconds=lease_seconds,
            default_features=features,
            api_client_secret=os.getenv("ALTERYX_LICENSE_API_CLIENT_SECRET", "").strip(),
        )

    def validate(self) -> None:
        """Validate production configuration requirements without leaking sensitive values."""
        if not self.key_vault_url:
            raise LicenseConfigurationError("AZURE_KEY_VAULT_URL is required.")
        if not self.key_vault_url.startswith("https://"):
            raise LicenseConfigurationError("AZURE_KEY_VAULT_URL must be a valid HTTPS URL.")
        if not self.private_key_secret_name:
            raise LicenseConfigurationError("AZURE_LICENSE_PRIVATE_KEY_SECRET_NAME is required.")
        if not self.default_license_id:
            raise LicenseConfigurationError("ALTERYX_LICENSE_ID is required.")
        if not self.default_product:
            raise LicenseConfigurationError("ALTERYX_LICENSE_PRODUCT is required.")
        if not self.default_environment:
            raise LicenseConfigurationError("ALTERYX_LICENSE_ENVIRONMENT is required.")
        valid_statuses = ("active", "expired", "revoked", "suspended", "invalid")
        if self.default_status not in valid_statuses:
            raise LicenseConfigurationError(
                f"ALTERYX_LICENSE_STATUS must be one of {valid_statuses}."
            )
        if not self.api_client_secret:
            raise LicenseConfigurationError("ALTERYX_LICENSE_API_CLIENT_SECRET is required.")
        if self.lease_seconds <= 0:
            raise LicenseConfigurationError(
                "ALTERYX_LICENSE_LEASE_SECONDS must be a positive integer."
            )
