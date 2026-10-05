"""Authoritative License Validation Service.

Executes business logic for license authentication, status evaluation,
lease issuance, and cryptographic binding of the response to the request.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from .canonical import canonical_payload
from .config import ServerConfig
from .models import (
    LicenseRecord,
    LicenseStatus,
    LicenseValidationRequest,
    LicenseValidationResponse,
)
from .repository import LicenseRepository
from .signer import LicenseSigner

logger = logging.getLogger("license_server.service")


class LicenseService:
    """Core license validation service."""

    def __init__(
        self,
        repository: LicenseRepository,
        signer: LicenseSigner,
        config: ServerConfig | None = None,
    ) -> None:
        """Initialize service with repository and signer dependencies."""
        self._repo = repository
        self._signer = signer
        self._config = config or ServerConfig.from_env()

    def validate_license(self, request: LicenseValidationRequest) -> LicenseValidationResponse:
        """Validate request against authoritative license records and return signed response.

        Args:
            request: Inbound validation request from client.

        Returns:
            Fully signed LicenseValidationResponse cryptographically bound to request.
        """
        server_now = datetime.now(timezone.utc)

        # 1. Look up license in repository
        record = self._repo.get_license(request.license_id)

        # Default values if license record not found
        if record is None:
            logger.warning(
                "License validation failed: unknown license_id=%s request_id=%s",
                request.license_id,
                request.request_id,
            )
            return self._build_and_sign_response(
                license_id=request.license_id,
                product=request.product,
                environment=request.environment,
                client_instance_id=request.client_instance_id,
                request_id=request.request_id,
                status=LicenseStatus.INVALID,
                lease_expires_at=server_now,
                server_time=server_now,
                features={},
                message="Unknown license identifier.",
            )

        # 2. Verify product match
        if request.product != record.product:
            logger.warning(
                "License validation failed: product mismatch requested=%s configured=%s license_id=%s",
                request.product,
                record.product,
                request.license_id,
            )
            return self._build_and_sign_response(
                license_id=record.license_id,
                product=record.product,
                environment=record.environment,
                client_instance_id=request.client_instance_id,
                request_id=request.request_id,
                status=LicenseStatus.INVALID,
                lease_expires_at=server_now,
                server_time=server_now,
                features={},
                message=f"Product mismatch: license is for '{record.product}'.",
            )

        # 3. Verify environment match
        if request.environment != record.environment:
            logger.warning(
                "License validation failed: environment mismatch requested=%s configured=%s license_id=%s",
                request.environment,
                record.environment,
                request.license_id,
            )
            return self._build_and_sign_response(
                license_id=record.license_id,
                product=record.product,
                environment=record.environment,
                client_instance_id=request.client_instance_id,
                request_id=request.request_id,
                status=LicenseStatus.INVALID,
                lease_expires_at=server_now,
                server_time=server_now,
                features={},
                message=f"Environment mismatch: license is for '{record.environment}'.",
            )

        # 4. Check absolute expiration date if configured
        if record.expires_at is not None and server_now >= record.expires_at:
            logger.info("License validation: contract expired at %s for license_id=%s", record.expires_at, record.license_id)
            return self._build_and_sign_response(
                license_id=record.license_id,
                product=record.product,
                environment=record.environment,
                client_instance_id=request.client_instance_id,
                request_id=request.request_id,
                status=LicenseStatus.EXPIRED,
                lease_expires_at=server_now,
                server_time=server_now,
                features=record.features,
                message="License has expired.",
            )

        # 5. Evaluate status and issue lease
        if record.status == LicenseStatus.ACTIVE:
            lease_expires_at = server_now + timedelta(seconds=self._config.lease_seconds)
            logger.info(
                "License validated: ACTIVE license_id=%s lease_expires_at=%s request_id=%s",
                record.license_id,
                lease_expires_at.isoformat(),
                request.request_id,
            )
            return self._build_and_sign_response(
                license_id=record.license_id,
                product=record.product,
                environment=record.environment,
                client_instance_id=request.client_instance_id,
                request_id=request.request_id,
                status=LicenseStatus.ACTIVE,
                lease_expires_at=lease_expires_at,
                server_time=server_now,
                features=record.features,
                message="License is active and in good standing.",
            )

        # Non-active status (EXPIRED, REVOKED, SUSPENDED, INVALID)
        logger.info(
            "License validated: non-active status=%s license_id=%s request_id=%s",
            record.status.value,
            record.license_id,
            request.request_id,
        )
        return self._build_and_sign_response(
            license_id=record.license_id,
            product=record.product,
            environment=record.environment,
            client_instance_id=request.client_instance_id,
            request_id=request.request_id,
            status=record.status,
            lease_expires_at=server_now,
            server_time=server_now,
            features=record.features,
            message=f"License status is {record.status.value}.",
        )

    def _build_and_sign_response(
        self,
        *,
        license_id: str,
        product: str,
        environment: str,
        client_instance_id: str,
        request_id: str,
        status: LicenseStatus,
        lease_expires_at: datetime,
        server_time: datetime,
        features: dict[str, bool],
        message: str,
    ) -> LicenseValidationResponse:
        """Construct response model, canonicalize with Pydantic JSON serialization, sign, and return."""
        response = LicenseValidationResponse(
            license_id=license_id,
            product=product,
            environment=environment,
            client_instance_id=client_instance_id,
            request_id=request_id,
            status=status,
            lease_expires_at=lease_expires_at,
            server_time=server_time,
            features=features,
            message=message,
            signature="",
        )

        # 1. Canonical payload bytes using Pydantic's exact JSON representation
        dumped_json_dict = response.model_dump(mode="json")
        canon_bytes = canonical_payload(dumped_json_dict)

        # 2. Cryptographic signature
        signature_b64 = self._signer.sign(canon_bytes)

        # 3. Assign signature
        response.signature = signature_b64
        return response
