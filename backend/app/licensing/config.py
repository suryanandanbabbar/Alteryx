"""License configuration loaded from environment variables.

The production Ed25519 public key can be embedded directly into this module
before Nuitka compilation, or overridden via ALTERYX_LICENSE_PUBLIC_KEY for
development/testing.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("awa.licensing.config")

# ---------------------------------------------------------------------------
# Production Ed25519 public key (base64-encoded, 32 bytes).
#
# CONFIGURATION REQUIRED:
#   Replace this value with the actual production public key before the
#   final Nuitka build.  The corresponding private key MUST remain in
#   Azure Key Vault and MUST NEVER appear in this file or repository.
#
#   Example (test-only, NOT a real production key):
#     _EMBEDDED_PUBLIC_KEY = "dGVzdC1wdWJsaWMta2V5LTMyLWJ5dGVzLXBhZA=="
# ---------------------------------------------------------------------------
_EMBEDDED_PUBLIC_KEY: str | None = None

# Default timing constants (seconds)
_DEFAULT_GRACE_SECONDS = 259_200      # 72 hours
_DEFAULT_HEARTBEAT_SECONDS = 3_600    # 1 hour


@dataclass(frozen=True)
class LicenseConfig:
    """Immutable license configuration.

    In production, licensing is permanently enabled and cannot be disabled
    via client environment variables. The production verification key is
    embedded directly into the application and cannot be overridden by
    ALTERYX_LICENSE_PUBLIC_KEY.
    """

    enabled: bool = True
    api_url: str = ""
    license_id: str = ""
    product: str = "alteryx-etl"
    environment: str = "production"
    public_key_b64: str | None = None
    grace_seconds: int = _DEFAULT_GRACE_SECONDS
    heartbeat_seconds: int = _DEFAULT_HEARTBEAT_SECONDS

    # ── Factory ──────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> LicenseConfig:
        """Build a :class:`LicenseConfig` from environment variables.

        Security Enforcement:
        - Licensing is permanently enabled in production builds.
          ALTERYX_LICENSE_ENABLED is NOT checked and cannot disable licensing.
        - The production public key is strictly the embedded _EMBEDDED_PUBLIC_KEY.
          ALTERYX_LICENSE_PUBLIC_KEY is NOT accepted in production to prevent
          clients from supplying their own keypairs.
        - Lease duration is authoritative on the Azure server side, so
          ALTERYX_LICENSE_LEASE_SECONDS is not configurable by the client.
        """
        # Production public key must be the embedded key, never an env override
        public_key = _EMBEDDED_PUBLIC_KEY

        return cls(
            enabled=True,
            api_url=os.getenv("ALTERYX_LICENSE_API_URL", "").strip(),
            license_id=os.getenv("ALTERYX_LICENSE_ID", "").strip(),
            product=os.getenv("ALTERYX_LICENSE_PRODUCT", "alteryx-etl").strip(),
            environment=os.getenv("ALTERYX_LICENSE_ENVIRONMENT", "production").strip(),
            public_key_b64=public_key if public_key else None,
            grace_seconds=int(
                os.getenv("ALTERYX_LICENSE_GRACE_SECONDS", str(_DEFAULT_GRACE_SECONDS))
            ),
            heartbeat_seconds=int(
                os.getenv("ALTERYX_LICENSE_HEARTBEAT_SECONDS", str(_DEFAULT_HEARTBEAT_SECONDS))
            ),
        )

    # ── Validation ───────────────────────────────────────────────────

    def validate(self) -> None:
        """Raise :class:`LicenseConfigurationError` if required fields are missing."""
        from .errors import LicenseConfigurationError

        if not self.enabled:
            return

        if not self.api_url:
            raise LicenseConfigurationError(
                "ALTERYX_LICENSE_API_URL is required when licensing is enabled."
            )
        if not self.license_id:
            raise LicenseConfigurationError(
                "ALTERYX_LICENSE_ID is required when licensing is enabled."
            )
        if not self.public_key_b64:
            raise LicenseConfigurationError(
                "Ed25519 public key is required. "
                "Embed the production public key in the build."
            )
