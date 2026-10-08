"""License manager — orchestrates signed license retrieval, cryptographic verification, and startup enforcement.

This is the single integration point between the licensing subsystem and
the application lifecycle. The application entry point calls
:meth:`LicenseManager.validate_or_raise` before continuing startup.

The signed license artifact policy is the SINGLE authoritative runtime policy.
"""

from __future__ import annotations

import json
import logging
import os
import signal
from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from pydantic import ValidationError

from .config import LicenseConfig
from .criteria import DateCriterion, TokenUsageCriterion, VolumeCriterion
from .errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseLimitExceededError,
    LicenseSecretError,
    LicenseSignatureError,
)
from .models import LicenseArtifact, LicenseState
from .secret_provider import SecretProvider
from .verifier import canonical_payload, validate_identity, verify_signature

if TYPE_CHECKING:
    from .usage_source import UsageDataSource

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
        volume_usage_source: UsageDataSource | None = None,
        token_usage_source: UsageDataSource | None = None,
        on_shutdown: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize LicenseManager with configuration and secret provider.

        Args:
            config: Optional explicit configuration. Defaults to :meth:`LicenseConfig.load`.
            secret_provider: Explicit SecretProvider. Required for validation.
            volume_usage_source: Optional usage source for volume criterion.
            token_usage_source: Optional usage source for token usage criterion.
            on_shutdown: Optional shutdown handler callback. Defaults to SIGTERM.
        """
        cfg = config or LicenseConfig.load()
        if volume_usage_source is not None or token_usage_source is not None:
            cfg = replace(
                cfg,
                volume_usage_source=volume_usage_source or cfg.volume_usage_source,
                token_usage_source=token_usage_source or cfg.token_usage_source,
            )
        self._config = cfg
        self._provider: SecretProvider | None = secret_provider

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

    @property
    def date_state(self) -> Any:
        """Validated date criterion result."""
        return self._state.date_state

    @property
    def volume_state(self) -> Any:
        """Validated volume criterion result."""
        return self._state.volume_state

    @property
    def token_state(self) -> Any:
        """Validated token usage criterion result."""
        return self._state.token_state

    # ── Startup enforcement ──────────────────────────────────────────

    def validate_or_raise(self) -> None:
        """Perform synchronous signed-license validation at startup.

        Executes:
        1. Configuration validation
        2. Secret retrieval from configured SecretProvider
        3. JSON parsing
        4. Strict schema validation (requires policy)
        5. Canonical serialization & Ed25519 signature verification
        6. Identity matching (license_id, product, environment)
        7. Single authoritative enforcement policy from signed artifact:
           - DateCriterion if artifact.policy.date.enabled
           - VolumeCriterion if artifact.policy.volume.enabled
           - TokenUsageCriterion if artifact.policy.token_usage.enabled
        8. Feature schema validation
        9. In-memory state persistence

        Raises:
            LicenseConfigurationError: Missing or invalid configuration / provider.
            LicenseSecretError: Secret scope/key unavailable or empty.
            LicenseInvalidError: Malformed JSON, schema violation, or identity mismatch.
            LicenseSignatureError: Signature verification failed.
            LicenseExpiredError: License expired against trusted UTC time.
            LicenseLimitExceededError: Volume or token usage limit reached/exceeded.
        """
        logger.info("Initializing license enforcement...")
        self._state = LicenseState(is_valid=False)

        # 1. Load & validate configuration
        self._config.validate()

        if self._provider is None:
            raise LicenseConfigurationError(
                "An explicit SecretProvider is required. Pass a valid SecretProvider instance to LicenseManager."
            )

        # 2. Retrieve the license JSON from SecretProvider
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

        # 4. Strict schema and feature validation via Pydantic (requires policy)
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

        # 7. Single authoritative enforcement policy from signed artifact
        # Date Criterion
        date_criterion = DateCriterion(
            enabled=artifact.policy.date.enabled,
            expires_at=artifact.expires_at,
            issued_at=artifact.issued_at,
        )
        date_res = date_criterion.validate()

        # Volume Criterion
        if artifact.policy.volume.enabled:
            if self._config.volume_usage_source is None:
                raise LicenseInvalidError(
                    "Signed license requires volume enforcement, but no volume usage source is configured."
                )
            vol_criterion = VolumeCriterion(
                enabled=True,
                limit=artifact.policy.volume.limit,
                usage_source=self._config.volume_usage_source,
                license_id=artifact.license_id,
            )
            vol_res = vol_criterion.validate()
        else:
            vol_criterion = VolumeCriterion(enabled=False, license_id=artifact.license_id)
            vol_res = vol_criterion.validate()

        # Token Usage Criterion
        if artifact.policy.token_usage.enabled:
            if self._config.token_usage_source is None:
                raise LicenseInvalidError(
                    "Signed license requires token usage enforcement, but no token usage source is configured."
                )
            tok_criterion = TokenUsageCriterion(
                enabled=True,
                limit=artifact.policy.token_usage.limit,
                usage_source=self._config.token_usage_source,
                license_id=artifact.license_id,
            )
            token_res = tok_criterion.validate()
        else:
            tok_criterion = TokenUsageCriterion(enabled=False, license_id=artifact.license_id)
            token_res = tok_criterion.validate()

        # 8. All verifications passed — store validated state in memory
        self._state = LicenseState(
            is_valid=True,
            license_id=artifact.license_id,
            product=artifact.product,
            environment=artifact.environment,
            issued_at=artifact.issued_at,
            expires_at=artifact.expires_at,
            features=artifact.features,
            policy=artifact.policy,
            date_state=date_res,
            volume_state=vol_res,
            token_state=token_res,
        )
        logger.info(
            "License validated successfully for license_id=%s product=%s env=%s. Date: %s, Volume: %s, Tokens: %s.",
            artifact.license_id,
            artifact.product,
            artifact.environment,
            date_res.message,
            vol_res.message,
            token_res.message,
        )

    # ── Shutdown mechanism ───────────────────────────────────────────

    @staticmethod
    def _default_shutdown(reason: str) -> None:
        """Default shutdown handler: send SIGTERM to trigger graceful process termination."""
        logger.critical(
            "LICENSE ENFORCEMENT: Initiating application shutdown — %s", reason
        )
        os.kill(os.getpid(), signal.SIGTERM)
