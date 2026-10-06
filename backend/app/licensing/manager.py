"""License manager — orchestrates Databricks Key Vault-backed signed license validation.

This is the single integration point between the licensing subsystem and
the FastAPI application lifecycle. The application entry point calls
:meth:`LicenseManager.validate_or_raise` before yielding.
"""

from __future__ import annotations

import json
import logging
import os
import signal
from datetime import datetime, timezone
from typing import Callable

from pydantic import ValidationError

from .config import LicenseConfig
from .errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseSecretError,
    LicenseSignatureError,
)
from .models import LicenseArtifact, LicenseState
from .secret_provider import DatabricksSecretProvider, SecretProvider
from .verifier import canonical_payload, validate_expiry, validate_identity, verify_signature

logger = logging.getLogger("awa.licensing.manager")


class LicenseManager:
    """Manages signed license retrieval, cryptographic verification, and lifecycle enforcement.

    Usage::

        mgr = LicenseManager()
        mgr.validate_or_raise()          # blocks startup if invalid
    """

    def __init__(
        self,
        config: LicenseConfig | None = None,
        secret_provider: SecretProvider | None = None,
        *,
        on_shutdown: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize LicenseManager with configuration and secret provider.

        Args:
            config: Optional explicit configuration. Defaults to :meth:`LicenseConfig.from_env`.
            secret_provider: Optional SecretProvider. Defaults to :class:`DatabricksSecretProvider`.
            on_shutdown: Optional shutdown handler callback. Defaults to SIGTERM.
        """
        self._config = config or LicenseConfig.from_env()
        self._provider = secret_provider or DatabricksSecretProvider()
        self._state: LicenseState = LicenseState()
        self._on_shutdown = on_shutdown or self._default_shutdown

    # ── Properties ───────────────────────────────────────────────────

    @property
    def config(self) -> LicenseConfig:
        """Active license configuration (read-only)."""
        return self._config

    @property
    def state(self) -> LicenseState:
        """Current validated in-memory license state."""
        return self._state

    @property
    def is_licensed(self) -> bool:
        """``True`` when the application holds a cryptographically validated, unexpired license."""
        return self._state.is_valid

    @property
    def features(self) -> dict[str, bool]:
        """Dictionary of approved feature flags."""
        return dict(self._state.features)

    def has_feature(self, feature_name: str) -> bool:
        """Check whether a specific feature is enabled in the active license."""
        return self._state.has_feature(feature_name)

    # ── Startup enforcement ──────────────────────────────────────────

    def validate_or_raise(self) -> None:
        """Perform synchronous signed-license validation at startup.

        Executes:
        1. Configuration validation
        2. Secret retrieval from Databricks scope
        3. JSON parsing
        4. Strict schema validation
        5. Canonical serialization & Ed25519 signature verification
        6. Identity matching (license_id, product, environment)
        7. Timestamp & UTC expiration check
        8. Feature schema validation
        9. In-memory state persistence

        Raises:
            LicenseConfigurationError: Missing or invalid configuration.
            LicenseSecretError: Secret scope/key unavailable or empty.
            LicenseInvalidError: Malformed JSON, schema violation, or identity mismatch.
            LicenseSignatureError: Signature verification failed.
            LicenseExpiredError: License expired against trusted UTC time.
        """
        logger.info("Initializing license enforcement from Databricks secret scope...")
        self._state = LicenseState(is_valid=False)

        # 1. Load & validate configuration
        self._config.validate()

        # 2. Retrieve the license JSON from Databricks Secret Scope
        secret_content = self._provider.get_secret(
            scope=self._config.secret_scope,
            key=self._config.secret_name,
        )

        # 3. Parse JSON
        try:
            raw_dict = json.loads(secret_content)
            if not isinstance(raw_dict, dict):
                raise LicenseInvalidError("License secret document must be a JSON object.")
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse license secret as JSON: %s", exc)
            raise LicenseInvalidError("Malformed JSON in license secret.") from exc

        # 4. Strict schema and feature validation via Pydantic
        try:
            artifact = LicenseArtifact.model_validate(raw_dict)
        except ValidationError as exc:
            logger.error("License artifact schema validation failed: %s", exc)
            raise LicenseInvalidError(f"License artifact schema error: {exc}") from exc

        # 5. Canonicalize & verify Ed25519 signature with embedded public key
        verify_signature(
            payload_dict=raw_dict,
            signature_b64=artifact.signature,
            public_key_b64=self._config.public_key_b64,
        )

        # 6. Validate identity rules
        validate_identity(
            artifact_license_id=artifact.license_id,
            artifact_product=artifact.product,
            artifact_environment=artifact.environment,
            expected_license_id=self._config.license_id,
            expected_product=self._config.product,
            expected_environment=self._config.environment,
        )

        # 7. Validate expiration against trusted application UTC time
        validate_expiry(expires_at=artifact.expires_at)

        # 8. All verifications passed — store validated state in memory
        self._state = LicenseState(
            is_valid=True,
            license_id=artifact.license_id,
            product=artifact.product,
            environment=artifact.environment,
            issued_at=artifact.issued_at,
            expires_at=artifact.expires_at,
            features=artifact.features,
        )
        logger.info(
            "License validated successfully for license_id=%s product=%s env=%s. Expires at %s UTC.",
            artifact.license_id,
            artifact.product,
            artifact.environment,
            artifact.expires_at.isoformat(),
        )

    # ── Shutdown mechanism ───────────────────────────────────────────

    @staticmethod
    def _default_shutdown(reason: str) -> None:
        """Default shutdown handler: send SIGTERM to trigger graceful process termination."""
        logger.critical(
            "LICENSE ENFORCEMENT: Initiating application shutdown — %s", reason
        )
        os.kill(os.getpid(), signal.SIGTERM)
