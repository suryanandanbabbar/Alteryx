"""Tests for the License Validation Service, Authentication, and FastAPI Endpoints.

Validates active, expired, revoked, suspended, and invalid license handling,
parameter matching, nonce echoing, Bearer API authentication, /health, /ready,
and client verification round-trip.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from license_server.config import ServerConfig
from license_server.errors import LicenseConfigurationError
from license_server.keyvault import AzureKeyVaultClient
from license_server.main import app, get_service
from license_server.models import (
    LicenseRecord,
    LicenseStatus,
    LicenseValidationRequest,
    LicenseValidationResponse,
)
from license_server.repository import LicenseRepository
from license_server.service import LicenseService
from license_server.signer import LicenseSigner
from backend.app.licensing.verifier import verify_signature

TEST_API_SECRET = "super-secret-license-api-token"
AUTH_HEADER = {"Authorization": f"Bearer {TEST_API_SECRET}"}


class InMemoryLicenseRepository(LicenseRepository):
    """In-memory repository for unit testing."""

    def __init__(self, records: dict[str, LicenseRecord] | None = None) -> None:
        self._records = records or {}

    def get_license(self, license_id: str) -> LicenseRecord | None:
        return self._records.get(license_id)


@pytest.fixture
def keypair():
    """Generate Ed25519 test keypair."""
    priv = ed25519.Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "private_b64": base64.b64encode(priv_bytes).decode("ascii"),
        "public_b64": base64.b64encode(pub_bytes).decode("ascii"),
    }


@pytest.fixture
def test_setup(keypair):
    """Setup test repo, signer, and service."""
    now = datetime.now(timezone.utc)
    records = {
        "LIC-ACTIVE": LicenseRecord(
            license_id="LIC-ACTIVE",
            product="alteryx-etl",
            environment="production",
            status=LicenseStatus.ACTIVE,
            expires_at=now + timedelta(days=30),
            features={"export_pdf": True, "sttm": True},
        ),
        "LIC-EXPIRED": LicenseRecord(
            license_id="LIC-EXPIRED",
            product="alteryx-etl",
            environment="production",
            status=LicenseStatus.EXPIRED,
            expires_at=now - timedelta(days=1),
        ),
        "LIC-REVOKED": LicenseRecord(
            license_id="LIC-REVOKED",
            product="alteryx-etl",
            environment="production",
            status=LicenseStatus.REVOKED,
        ),
        "LIC-SUSPENDED": LicenseRecord(
            license_id="LIC-SUSPENDED",
            product="alteryx-etl",
            environment="production",
            status=LicenseStatus.SUSPENDED,
        ),
    }
    repo = InMemoryLicenseRepository(records)

    kv_mock = MagicMock(spec=AzureKeyVaultClient)
    kv_mock.get_secret.return_value = keypair["private_b64"]
    signer = LicenseSigner(key_vault_client=kv_mock, secret_name="signing-key")

    config = ServerConfig(
        key_vault_url="https://test-vault.vault.azure.net",
        default_license_id="LIC-ACTIVE",
        lease_seconds=3600,
        api_client_secret=TEST_API_SECRET,
    )
    service = LicenseService(repository=repo, signer=signer, config=config)

    # Set app state and dependency overrides
    app.state.config = config
    app.state.service = service
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    yield {
        "client": client,
        "service": service,
        "repo": repo,
        "public_b64": keypair["public_b64"],
        "config": config,
    }
    app.dependency_overrides.clear()


def test_health_check(test_setup):
    """GET /health must return 200 and healthy status without calling Key Vault."""
    client = test_setup["client"]
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "service": "alteryx-license-api"}


def test_readiness_check_success(test_setup):
    """GET /ready returns 200 when minimum required configuration is present."""
    client = test_setup["client"]
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "service": "alteryx-license-api"}


def test_readiness_check_not_ready():
    """GET /ready returns 503 when required configuration is missing."""
    unconfigured = ServerConfig(key_vault_url="", default_license_id="")
    app.state.config = unconfigured
    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Service is not ready (missing required configuration)."


def test_authentication_missing_header(test_setup):
    """POST /v1/license/validate without Authorization header must return HTTP 401."""
    client = test_setup["client"]
    req_payload = {
        "license_id": "LIC-ACTIVE",
        "product": "alteryx-etl",
        "client_instance_id": "client-1",
        "environment": "production",
        "request_id": "nonce-1",
    }
    resp = client.post("/v1/license/validate", json=req_payload)
    assert resp.status_code == 401
    assert "WWW-Authenticate" in resp.headers


def test_authentication_invalid_secret(test_setup):
    """POST /v1/license/validate with wrong Bearer token must return HTTP 401."""
    client = test_setup["client"]
    req_payload = {
        "license_id": "LIC-ACTIVE",
        "product": "alteryx-etl",
        "client_instance_id": "client-1",
        "environment": "production",
        "request_id": "nonce-1",
    }
    resp = client.post(
        "/v1/license/validate",
        json=req_payload,
        headers={"Authorization": "Bearer wrong-client-secret-token"},
    )
    assert resp.status_code == 401


def test_validate_active_license_roundtrip(test_setup):
    """Active license validation with valid auth returns HTTP 200, status active, and valid client signature."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-ACTIVE",
        "product": "alteryx-etl",
        "client_instance_id": "client-instance-uuid-1234",
        "environment": "production",
        "request_id": "random-nonce-abc-987",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "active"
    assert data["license_id"] == "LIC-ACTIVE"
    assert data["product"] == "alteryx-etl"
    assert data["environment"] == "production"
    assert data["client_instance_id"] == "client-instance-uuid-1234"
    assert data["request_id"] == "random-nonce-abc-987"
    assert data["features"] == {"export_pdf": True, "sttm": True}
    assert "signature" in data

    # Client verification must pass 100%
    is_valid = verify_signature(
        payload_dict=data,
        signature_b64=data["signature"],
        public_key_b64=pub_key,
    )
    assert is_valid is True

    # Client Pydantic model parsing must succeed
    from backend.app.licensing.models import LicenseValidationResponse as ClientResponse

    client_model = ClientResponse(**data)
    assert client_model.status.value == "active"
    assert client_model.license_id == "LIC-ACTIVE"
    assert client_model.request_id == "random-nonce-abc-987"


def test_validate_expired_license(test_setup):
    """Expired license must return status expired and signed response."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-EXPIRED",
        "product": "alteryx-etl",
        "client_instance_id": "client-456",
        "environment": "production",
        "request_id": "nonce-expired",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "expired"
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_revoked_license(test_setup):
    """Revoked license must return status revoked and signed response."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-REVOKED",
        "product": "alteryx-etl",
        "client_instance_id": "client-789",
        "environment": "production",
        "request_id": "nonce-revoked",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "revoked"
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_suspended_license(test_setup):
    """Suspended license must return status suspended and signed response."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-SUSPENDED",
        "product": "alteryx-etl",
        "client_instance_id": "client-sus",
        "environment": "production",
        "request_id": "nonce-suspended",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "suspended"
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_unknown_license_id(test_setup):
    """Unknown license ID must return status invalid."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "DOES-NOT-EXIST",
        "product": "alteryx-etl",
        "client_instance_id": "client-x",
        "environment": "production",
        "request_id": "nonce-unknown",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "invalid"
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_product_mismatch(test_setup):
    """Product mismatch must return status invalid."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-ACTIVE",
        "product": "wrong-product-name",
        "client_instance_id": "client-y",
        "environment": "production",
        "request_id": "nonce-prod-mismatch",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "invalid"
    assert "Product mismatch" in data["message"]
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_environment_mismatch(test_setup):
    """Environment mismatch must return status invalid."""
    client = test_setup["client"]
    pub_key = test_setup["public_b64"]

    req_payload = {
        "license_id": "LIC-ACTIVE",
        "product": "alteryx-etl",
        "client_instance_id": "client-z",
        "environment": "staging",  # license is production
        "request_id": "nonce-env-mismatch",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "invalid"
    assert "Environment mismatch" in data["message"]
    assert verify_signature(data, data["signature"], pub_key) is True


def test_validate_malformed_request_returns_422(test_setup):
    """Missing required fields in request payload must return HTTP 422."""
    client = test_setup["client"]
    bad_payload = {"license_id": "LIC-ACTIVE"}

    resp = client.post("/v1/license/validate", json=bad_payload, headers=AUTH_HEADER)
    assert resp.status_code == 422


def test_server_config_validation():
    """Verify ServerConfig.validate() enforces required production settings."""
    cfg = ServerConfig(
        key_vault_url="https://vault.azure.net",
        private_key_secret_name="alteryx-license-private-key",
        default_license_id="LIC-1",
        default_product="alteryx-etl",
        default_environment="production",
        default_status="active",
        api_client_secret="test-secret",
        lease_seconds=86400,
    )
    # Valid config should not raise
    cfg.validate()

    # Missing API client secret
    cfg_no_secret = ServerConfig(
        key_vault_url="https://vault.azure.net",
        default_license_id="LIC-1",
        api_client_secret="",
    )
    with pytest.raises(LicenseConfigurationError) as exc_info:
        cfg_no_secret.validate()
    assert "ALTERYX_LICENSE_API_CLIENT_SECRET is required" in str(exc_info.value)

    # Missing Key Vault URL
    cfg_no_kv = ServerConfig(
        key_vault_url="",
        default_license_id="LIC-1",
        api_client_secret="secret",
    )
    with pytest.raises(LicenseConfigurationError) as exc_info:
        cfg_no_kv.validate()
    assert "AZURE_KEY_VAULT_URL is required" in str(exc_info.value)
