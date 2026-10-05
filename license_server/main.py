"""FastAPI Application for the Azure License API Server.

Serves as the authoritative licensing endpoint for the Alteryx ETL Rationalisation
application. Validates license requests, verifies environment and product bindings,
and issues cryptographically signed Ed25519 lease responses.
"""

from __future__ import annotations

import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import ServerConfig
from .errors import AuthenticationError, KeyVaultError, LicenseConfigurationError, LicenseServerError, SigningError
from .keyvault import AzureKeyVaultClient
from .models import LicenseValidationRequest, LicenseValidationResponse
from .repository import EnvironmentLicenseRepository, LicenseRepository
from .service import LicenseService
from .signer import LicenseSigner

logger = logging.getLogger("license_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

bearer_scheme = HTTPBearer(auto_error=False)


def create_default_service(config: ServerConfig | None = None) -> LicenseService:
    """Factory creating the production LicenseService wiring."""
    cfg = config or ServerConfig.from_env()
    kv_client = AzureKeyVaultClient(vault_url=cfg.key_vault_url)
    signer = LicenseSigner(
        key_vault_client=kv_client,
        secret_name=cfg.private_key_secret_name,
    )
    repo = EnvironmentLicenseRepository(config=cfg)
    return LicenseService(repository=repo, signer=signer, config=cfg)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    logger.info("Initializing Azure License API Server...")
    config = ServerConfig.from_env()
    app.state.config = config
    # Lazily initialize default service if not already provided (e.g. by tests)
    if not hasattr(app.state, "service") or app.state.service is None:
        try:
            app.state.service = create_default_service(config)
            logger.info("LicenseService initialized successfully.")
        except Exception as exc:
            logger.warning(
                "LicenseService lazy init deferred (Key Vault URL may be unconfigured): %s",
                type(exc).__name__,
            )
            app.state.service = None
    yield
    logger.info("Azure License API Server shutting down.")


app = FastAPI(
    title="Alteryx License Authority API",
    description="Authoritative Ed25519 license validation and lease issuance service.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_service(request: Request) -> LicenseService:
    """FastAPI dependency to retrieve the active LicenseService."""
    service = getattr(request.app.state, "service", None)
    if service is None:
        # Attempt just-in-time creation
        try:
            config = getattr(request.app.state, "config", None) or ServerConfig.from_env()
            service = create_default_service(config)
            request.app.state.service = service
        except Exception as exc:
            logger.error("Failed to initialize LicenseService on demand: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Licensing service is temporarily unavailable.",
            ) from exc
    return service


def verify_api_secret(
    request: Request,
    auth_credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    """Validate Bearer authentication token against ALTERYX_LICENSE_API_CLIENT_SECRET.

    Executes constant-time comparison to prevent timing attacks.
    Never logs or reflects received or expected secrets.
    """
    config: ServerConfig = getattr(request.app.state, "config", None) or ServerConfig.from_env()
    expected_secret = config.api_client_secret

    if not expected_secret:
        logger.error("API client secret is not configured on the server.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error.",
        )

    if not auth_credentials or not auth_credentials.credentials:
        logger.warning("Validation request rejected: missing or malformed Authorization header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(auth_credentials.credentials, expected_secret):
        logger.warning("Validation request rejected: invalid API client secret.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Custom error handling to prevent internal leakages
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors without leaking sensitive data."""
    logger.warning("Invalid request format received: %s", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request payload format."},
    )


@app.exception_handler(KeyVaultError)
async def keyvault_exception_handler(request: Request, exc: KeyVaultError) -> JSONResponse:
    """Handle Key Vault access errors safely without exposing internal details."""
    logger.error("Key Vault error encountered: %s", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Cryptographic signing authority temporarily unavailable."},
    )


@app.exception_handler(SigningError)
async def signing_exception_handler(request: Request, exc: SigningError) -> JSONResponse:
    """Handle signing errors safely without exposing key or cryptographic material."""
    logger.error("Cryptographic signing error: %s", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Failed to sign license response."},
    )


@app.exception_handler(LicenseConfigurationError)
async def config_exception_handler(
    request: Request, exc: LicenseConfigurationError
) -> JSONResponse:
    """Handle server configuration errors safely."""
    logger.error("Configuration error: %s", str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Server configuration error."},
    )


@app.exception_handler(LicenseServerError)
async def license_server_error_handler(
    request: Request, exc: LicenseServerError
) -> JSONResponse:
    """Catch-all for license server domain errors."""
    logger.error("Domain error: %s", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal license service error."},
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness probe endpoint. Does not trigger live Key Vault requests."""
    return {"status": "healthy", "service": "alteryx-license-api"}


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(request: Request) -> dict[str, str]:
    """Readiness probe endpoint. Verifies configuration presence without live Key Vault call."""
    config: ServerConfig = getattr(request.app.state, "config", None) or ServerConfig.from_env()
    # Check minimum required configuration to serve validation requests
    if not config.key_vault_url or not config.default_license_id or not config.api_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is not ready (missing required configuration).",
        )
    return {"status": "ready", "service": "alteryx-license-api"}


@app.post(
    "/v1/license/validate",
    response_model=LicenseValidationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_secret)],
)
async def validate_license_endpoint(
    validation_request: LicenseValidationRequest,
    service: LicenseService = Depends(get_service),
) -> LicenseValidationResponse:
    """Validate incoming client license request and return signed authoritative lease.

    Enforces Bearer authentication before processing.
    Logs non-sensitive validation details (request_id, client_instance_id, license_id).
    Never logs private keys, secrets, or internal memory structures.
    """
    start_time = time.monotonic()
    logger.info(
        "Validation request received: license_id=%s product=%s env=%s client_id=%s req_id=%s",
        validation_request.license_id,
        validation_request.product,
        validation_request.environment,
        validation_request.client_instance_id,
        validation_request.request_id,
    )

    response = service.validate_license(validation_request)
    duration_ms = (time.monotonic() - start_time) * 1000

    logger.info(
        "Validation completed: license_id=%s status=%s req_id=%s duration=%.2fms",
        response.license_id,
        response.status.value,
        response.request_id,
        duration_ms,
    )

    return response
