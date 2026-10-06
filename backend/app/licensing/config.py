"""License configuration loaded from environment variables.

In production, licensing validates a signed artifact retrieved from
a Databricks Azure Key Vault-backed secret scope.
The Ed25519 public verification key is embedded directly into this module.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from .errors import LicenseConfigurationError

logger = logging.getLogger("awa.licensing.config")

# ---------------------------------------------------------------------------
# Canonical Production License Constants (Immutable Build-Time Values)
# ---------------------------------------------------------------------------
# Production Ed25519 public key (base64-encoded, 32 bytes).
# Extracted from alteryx-license-public.pem.
# The corresponding private key resides exclusively in the private Azure
# Key Vault (alteryx-licensing) and is NEVER included in client builds.
_EMBEDDED_PUBLIC_KEY: str = "aykIwjC0U0mxmTXUDhQdwBCiogj8YRNWy/8EieAfx9s="

_PRODUCTION_SECRET_SCOPE: str = "alteryx-licenseArtifacts"
_PRODUCTION_SECRET_NAME: str = "alteryx-license"
_PRODUCTION_LICENSE_ID: str = "CLIENT-ALTERYX-001"
_PRODUCTION_PRODUCT: str = "alteryx-etl"
_PRODUCTION_ENVIRONMENT: str = "production"


@dataclass(frozen=True)
class LicenseConfig:
    """Immutable license configuration.

    In production, licensing is permanently enabled and cannot be disabled
    via client environment variables. The production verification key, identity
    (license_id, product, environment), and secret scope/key are immutable
    constants embedded directly into the application and cannot be overridden
    by environment variables.
    """

    secret_scope: str = _PRODUCTION_SECRET_SCOPE
    secret_name: str = _PRODUCTION_SECRET_NAME
    license_id: str = _PRODUCTION_LICENSE_ID
    product: str = _PRODUCTION_PRODUCT
    environment: str = _PRODUCTION_ENVIRONMENT
    public_key_b64: str = _EMBEDDED_PUBLIC_KEY

    @property
    def enabled(self) -> bool:
        """Licensing is permanently enabled in production."""
        return True

    @classmethod
    def from_env(cls) -> LicenseConfig:
        """Build the immutable production :class:`LicenseConfig`.

        Security Enforcement:
        - Production identity (license_id, product, environment) is bound
          immutably to canonical build-time constants. Environment variables
          (ALTERYX_LICENSE_ID, ALTERYX_LICENSE_PRODUCT, ALTERYX_LICENSE_ENVIRONMENT)
          are strictly ignored to prevent customer identity tampering.
        - Secret scope and secret key are bound to the production Databricks scope
          (alteryx-licenseArtifacts / alteryx-license) and cannot be redirected
          via ALTERYX_LICENSE_SECRET_SCOPE or ALTERYX_LICENSE_SECRET_NAME.
        - Public verification key is strictly the embedded _EMBEDDED_PUBLIC_KEY.
          ALTERYX_LICENSE_PUBLIC_KEY is ignored.
        - Disable attempts (ALTERYX_LICENSE_ENABLED=false, LICENSE_ENABLED=false,
          ALTERYX_DISABLE_LICENSE=true) are completely ineffective.
        """
        return cls(
            secret_scope=_PRODUCTION_SECRET_SCOPE,
            secret_name=_PRODUCTION_SECRET_NAME,
            license_id=_PRODUCTION_LICENSE_ID,
            product=_PRODUCTION_PRODUCT,
            environment=_PRODUCTION_ENVIRONMENT,
            public_key_b64=_EMBEDDED_PUBLIC_KEY,
        )

    def validate(self) -> None:
        """Raise :class:`LicenseConfigurationError` if required fields are missing."""
        if not self.secret_scope:
            raise LicenseConfigurationError("Secret scope is required.")
        if not self.secret_name:
            raise LicenseConfigurationError("Secret name is required.")
        if not self.license_id:
            raise LicenseConfigurationError("License ID is required.")
        if not self.product:
            raise LicenseConfigurationError("Product is required.")
        if not self.environment:
            raise LicenseConfigurationError("Environment is required.")
        if not self.public_key_b64:
            raise LicenseConfigurationError(
                "Ed25519 public key is required. Embed the production public key in the build."
            )
