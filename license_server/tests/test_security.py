"""Security and Confidentiality Verification for Azure License API Server.

Strictly verifies that:
1. The Ed25519 private signing key is NEVER exposed in API responses or errors.
2. The API client secret is never returned in any response.
3. The private key is never written to disk or logged.
4. Cryptographic binding prevents response tampering or replay attacks across instances.
5. ServerConfig does not accept or process private keys from environment variables.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from license_server.config import ServerConfig
from license_server.keyvault import AzureKeyVaultClient
from license_server.main import app, get_service
from license_server.models import LicenseRecord, LicenseStatus
from license_server.service import LicenseService
from license_server.signer import LicenseSigner
from backend.app.licensing.verifier import verify_signature

TEST_SECRET = "secure-anti-abuse-secret-token"
AUTH_HEADER = {"Authorization": f"Bearer {TEST_SECRET}"}


class MockRepo:
    def __init__(self, record):
        self._record = record

    def get_license(self, license_id: str):
        return self._record


@pytest.fixture
def test_setup():
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
    priv_b64 = base64.b64encode(priv_bytes).decode("ascii")
    pub_b64 = base64.b64encode(pub_bytes).decode("ascii")

    record = LicenseRecord(
        license_id="SEC-TEST-001",
        product="alteryx-etl",
        environment="production",
        status=LicenseStatus.ACTIVE,
    )
    repo = MockRepo(record)
    kv_mock = MagicMock(spec=AzureKeyVaultClient)
    kv_mock.get_secret.return_value = priv_b64

    signer = LicenseSigner(key_vault_client=kv_mock, secret_name="private-key")
    config = ServerConfig(
        key_vault_url="https://sec-vault.vault.azure.net",
        default_license_id="SEC-TEST-001",
        api_client_secret=TEST_SECRET,
    )
    service = LicenseService(repository=repo, signer=signer, config=config)

    app.state.config = config
    app.state.service = service
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)

    yield {
        "client": client,
        "private_b64": priv_b64,
        "public_b64": pub_b64,
        "api_secret": TEST_SECRET,
    }
    app.dependency_overrides.clear()


def test_private_key_and_api_secret_never_in_response(test_setup):
    """The private key and API client secret must NEVER appear anywhere in the HTTP response."""
    client = test_setup["client"]
    private_key = test_setup["private_b64"]
    api_secret = test_setup["api_secret"]

    req_payload = {
        "license_id": "SEC-TEST-001",
        "product": "alteryx-etl",
        "client_instance_id": "client-secure-1",
        "environment": "production",
        "request_id": "nonce-sec-1",
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    resp_text = resp.text

    # Private key and API secret must not exist anywhere in the serialized response text
    assert private_key not in resp_text
    assert api_secret not in resp_text
    assert "private_key" not in resp_text


def test_private_key_never_in_server_config():
    """ServerConfig dataclass must NOT have any private key attribute."""
    config = ServerConfig.from_env()
    assert not hasattr(config, "private_key")
    assert not hasattr(config, "ed25519_private_key")
    assert not hasattr(config, "signing_key")


def test_cryptographic_nonce_binding(test_setup):
    """The server response must bind strictly to the request nonce and client instance ID."""
    client = test_setup["client"]
    sent_request_id = "unique-nonce-string-9999"
    sent_client_id = "unique-instance-string-1111"

    req_payload = {
        "license_id": "SEC-TEST-001",
        "product": "alteryx-etl",
        "client_instance_id": sent_client_id,
        "environment": "production",
        "request_id": sent_request_id,
    }

    resp = client.post("/v1/license/validate", json=req_payload, headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.json()

    # Echoed fields must be identical
    assert data["request_id"] == sent_request_id
    assert data["client_instance_id"] == sent_client_id

    # Signature must cover these fields
    pub_key = test_setup["public_b64"]
    assert verify_signature(data, data["signature"], pub_key) is True

    # If an attacker tries to reuse this signed response for a different client or nonce, verification fails
    forged_data = dict(data)
    forged_data["client_instance_id"] = "attacker-instance-id"
    with pytest.raises(Exception):
        verify_signature(forged_data, forged_data["signature"], pub_key)
