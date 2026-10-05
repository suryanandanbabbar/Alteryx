"""License manager — orchestrates validation, renewal, and enforcement.

This is the single integration point between the licensing subsystem and
the FastAPI application lifecycle.  The application entry point calls
:meth:`LicenseManager.validate_or_raise` before yielding, and
:meth:`LicenseManager.start_renewal_loop` / ``stop_renewal_loop`` to
manage the background lease heartbeat.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Callable

from .config import LicenseConfig
from .errors import (
    LicenseAuthenticationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseNetworkError,
    LicenseRevokedError,
    LicenseSignatureError,
)
from .models import LeaseState, LicenseStatus

logger = logging.getLogger("awa.licensing.manager")


class LicenseManager:
    """Manages the full license validation lifecycle.

    Usage::

        mgr = LicenseManager()
        mgr.validate_or_raise()          # blocks startup if invalid
        await mgr.start_renewal_loop()   # background heartbeat
        ...
        await mgr.stop_renewal_loop()    # graceful shutdown
    """

    def __init__(
        self,
        config: LicenseConfig | None = None,
        *,
        on_shutdown: Callable[[str], None] | None = None,
    ) -> None:
        """
        Args:
            config: Optional explicit configuration.  Defaults to
                :meth:`LicenseConfig.from_env`.
            on_shutdown: Optional callback invoked when the license
                becomes invalid at runtime.  Receives a human-readable
                reason string.  Defaults to sending ``SIGTERM`` to the
                current process (triggering graceful uvicorn shutdown).
        """
        self._config = config or LicenseConfig.from_env()
        self._lease = LeaseState()
        self._renewal_task: asyncio.Task[None] | None = None
        self._shutdown_event = asyncio.Event()
        self._on_shutdown = on_shutdown or self._default_shutdown

    # ── Properties ───────────────────────────────────────────────────

    @property
    def config(self) -> LicenseConfig:
        """Active license configuration (read-only)."""
        return self._config

    @property
    def lease(self) -> LeaseState:
        """Current in-memory lease state."""
        return self._lease

    @property
    def is_licensed(self) -> bool:
        """``True`` when the application has a valid license or licensing is disabled."""
        if not self._config.enabled:
            return True
        return self._lease.valid

    # ── Startup enforcement ──────────────────────────────────────────

    def validate_or_raise(self) -> None:
        """Perform synchronous license validation.

        This is the primary startup enforcement point.  It MUST be called
        before the application becomes operational.

        Raises:
            LicenseConfigurationError: Missing or invalid config.
            LicenseExpiredError: License expired or API unreachable
                without a valid lease.
            LicenseRevokedError: License revoked.
            LicenseSignatureError: Ed25519 verification failed.
            LicenseInvalidError: Malformed response or unrecognised status.
        """
        if not self._config.enabled:
            logger.info("License enforcement is disabled.")
            return

        # Validate configuration completeness
        self._config.validate()

        logger.info("Performing initial license validation against Azure License API...")

        try:
            self._perform_validation()
        except LicenseNetworkError as exc:
            # No previous successful lease → fail closed
            if not self._lease.is_within_grace(self._config.grace_seconds):
                raise LicenseExpiredError(
                    "License validation failed: Azure License API is unreachable "
                    "and no valid lease exists."
                ) from exc
            logger.warning(
                "Azure License API unreachable at startup, but an existing lease "
                "is within the configured grace period."
            )

    # ── Core validation ──────────────────────────────────────────────

    def _perform_validation(self) -> None:
        """Execute a single validation cycle (network call + crypto verify + binding checks).

        Raises appropriate license exceptions on any failure.
        """
        import secrets
        from .client import get_instance_id, validate_license
        from .verifier import verify_signature

        nonce = secrets.token_urlsafe(32)

        # Contact Azure License API with cryptographic nonce
        try:
            res = validate_license(self._config, request_id=nonce)
            raw_dict, response = res[0], res[1]
            sent_request_id = res[2]
            sent_instance_id = res[3] if len(res) > 3 else get_instance_id()
        except LicenseNetworkError:
            self._lease.record_failure()
            raise

        # 1. Verify Ed25519 signature over canonical payload (which covers request_id, client_instance_id, etc.)
        verify_signature(
            payload_dict=raw_dict,
            signature_b64=raw_dict.get("signature", ""),
            public_key_b64=self._config.public_key_b64,
        )

        # 2. Cryptographic binding verification: Request ID / Nonce
        if response.request_id != sent_request_id:
            raise LicenseInvalidError(
                f"Protocol binding error: response request_id '{response.request_id}' "
                f"does not match sent nonce '{sent_request_id}'."
            )

        # 3. Client instance ID binding verification
        if response.client_instance_id != sent_instance_id:
            raise LicenseInvalidError(
                f"Client instance mismatch: response client_instance_id '{response.client_instance_id}' "
                f"does not match requested instance ID '{sent_instance_id}'."
            )

        # 4. Identity verification: License ID
        if response.license_id != self._config.license_id:
            raise LicenseInvalidError(
                f"License ID mismatch: response license_id '{response.license_id}' "
                f"does not match configured license_id '{self._config.license_id}'."
            )

        # 4. Product binding verification
        if response.product != self._config.product:
            raise LicenseInvalidError(
                f"Product mismatch: response product '{response.product}' "
                f"does not match configured product '{self._config.product}'."
            )

        # 5. Environment binding verification
        if response.environment != self._config.environment:
            raise LicenseInvalidError(
                f"Environment mismatch: response environment '{response.environment}' "
                f"does not match configured environment '{self._config.environment}'."
            )

        # 6. Authoritative status enforcement
        if response.status == LicenseStatus.EXPIRED:
            self._lease.valid = False
            raise LicenseExpiredError(
                "License has expired. Contact your administrator."
            )

        if response.status == LicenseStatus.REVOKED:
            self._lease.valid = False
            raise LicenseRevokedError(
                "License has been revoked. Contact your administrator."
            )

        if response.status == LicenseStatus.SUSPENDED:
            self._lease.valid = False
            raise LicenseExpiredError(
                "License has been suspended. Contact your administrator."
            )

        if response.status != LicenseStatus.ACTIVE:
            raise LicenseInvalidError(
                f"Unrecognised license status '{response.status.value}'. "
                "Application cannot proceed."
            )

        # All verifications passed — update lease state
        self._lease.update_from_response(response)
        logger.info(
            "License validated successfully. Lease expires at %s (server time: %s).",
            response.lease_expires_at.isoformat(),
            response.server_time.isoformat(),
        )

    # ── Background renewal ───────────────────────────────────────────

    async def start_renewal_loop(self) -> None:
        """Start the background lease renewal task."""
        if not self._config.enabled:
            return
        self._shutdown_event.clear()
        self._renewal_task = asyncio.create_task(
            self._renewal_loop(), name="license-renewal"
        )
        logger.info(
            "License renewal task started (heartbeat every %d seconds).",
            self._config.heartbeat_seconds,
        )

    async def stop_renewal_loop(self) -> None:
        """Stop the background renewal task gracefully."""
        self._shutdown_event.set()
        if self._renewal_task is not None:
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
            self._renewal_task = None
            logger.info("License renewal task stopped.")

    async def _renewal_loop(self) -> None:
        """Background coroutine that periodically renews the lease."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self._config.heartbeat_seconds)
            except asyncio.CancelledError:
                break

            if self._shutdown_event.is_set():
                break

            try:
                # Run synchronous validation in thread-pool executor
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._perform_validation)
                logger.debug("License lease renewed successfully.")

            except (LicenseExpiredError, LicenseRevokedError) as exc:
                logger.error(
                    "License expired/revoked during runtime: %s. "
                    "Application will shut down.",
                    exc,
                )
                self._lease.valid = False
                self._on_shutdown(str(exc))
                break

            except LicenseSignatureError as exc:
                logger.error(
                    "License signature verification failed during renewal: %s. "
                    "Application will shut down.",
                    exc,
                )
                self._lease.valid = False
                self._on_shutdown(str(exc))
                break

            except LicenseInvalidError as exc:
                logger.error(
                    "Invalid license/protocol response received during renewal: %s. "
                    "Application will shut down immediately.",
                    exc,
                )
                self._lease.valid = False
                self._on_shutdown(str(exc))
                break

            except LicenseAuthenticationError as exc:
                logger.error(
                    "License API authentication failed during renewal: %s. "
                    "Application will shut down immediately without grace.",
                    exc,
                )
                self._lease.valid = False
                self._on_shutdown(str(exc))
                break

            except LicenseNetworkError as exc:
                logger.warning("License API unavailable during renewal: %s", exc)
                if not self._lease.is_within_grace(self._config.grace_seconds):
                    logger.error(
                        "Grace period exceeded. Application will shut down."
                    )
                    self._lease.valid = False
                    self._on_shutdown("License grace period exceeded.")
                    break
                logger.info(
                    "Existing lease within grace period. "
                    "Will retry in %d seconds.",
                    self._config.heartbeat_seconds,
                )

            except Exception as exc:
                logger.error(
                    "Unexpected error during license renewal: %s — %s",
                    type(exc).__name__,
                    str(exc)[:200],
                )
                self._lease.record_failure()
                if not self._lease.is_within_grace(self._config.grace_seconds):
                    logger.error(
                        "Grace period exceeded after unexpected error. "
                        "Application will shut down."
                    )
                    self._lease.valid = False
                    self._on_shutdown(
                        "License validation failed beyond grace period."
                    )
                    break

    # ── Shutdown mechanism ───────────────────────────────────────────

    @staticmethod
    def _default_shutdown(reason: str) -> None:
        """Default shutdown handler: send SIGTERM to trigger graceful uvicorn exit."""
        logger.critical(
            "LICENSE ENFORCEMENT: Initiating application shutdown — %s", reason
        )
        os.kill(os.getpid(), signal.SIGTERM)
