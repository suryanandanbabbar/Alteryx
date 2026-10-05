"""Comprehensive production security tests for the Azure-backed Ed25519 licensing subsystem.

Test requirements coverage (Section 10):
 1. valid signed response
 2. invalid signature
 3. malformed signature
 4. wrong public key
 5. wrong license ID
 6. wrong product
 7. wrong environment
 8. wrong request_id
 9. missing request_id
10. expired lease
11. revoked license
12. suspended license
13. startup with API unavailable and no previous lease
14. runtime API outage within grace
15. runtime API outage beyond grace
16. successful heartbeat renewal
17. failed heartbeat does not destroy a previously valid lease
18. production licensing cannot be disabled with ALTERYX_LICENSE_ENABLED=false
19. production public key cannot be replaced through ALTERYX_LICENSE_PUBLIC_KEY
20. canonicalization is deterministic
21. signature covers request_id
22. license ID mismatch after valid signature is rejected
"""

from __future__ import annotations

import base64
import json
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from nacl.signing import SigningKey

from backend.app.licensing.client import get_instance_id
from backend.app.licensing.config import LicenseConfig
from backend.app.licensing.errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseNetworkError,
    LicenseRevokedError,
    LicenseSignatureError,
)
from backend.app.licensing.manager import LicenseManager
from backend.app.licensing.models import (
    LeaseState,
    LicenseStatus,
    LicenseValidationResponse,
)
from backend.app.licensing.verifier import canonical_payload, verify_signature


# ── Test Fixtures & Helpers ──────────────────────────────────────────


@pytest.fixture
def test_keypair():
    """Generate a temporary Ed25519 keypair strictly for testing.

    SECURITY: Never use or store production keys in tests.
    """
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    priv_b64 = base64.b64encode(signing_key.encode()).decode("ascii")
    pub_b64 = base64.b64encode(verify_key.encode()).decode("ascii")
    return {
        "signing_key": signing_key,
        "verify_key": verify_key,
        "private_b64": priv_b64,
        "public_b64": pub_b64,
    }


def make_signed_payload(
    signing_key: SigningKey,
    *,
    license_id: str = "TEST-LIC-001",
    product: str = "alteryx-etl",
    environment: str = "production",
    request_id: str = "test-nonce-12345",
    client_instance_id: str | None = None,
    status: str = "active",
    lease_hours: int = 24,
    server_time: datetime | None = None,
    features: dict | None = None,
    message: str = "OK",
) -> tuple[dict, str]:
    """Helper to construct a valid response payload signed with a test key."""
    st = server_time or datetime.now(timezone.utc)
    exp = st + timedelta(hours=lease_hours)
    inst_id = client_instance_id if client_instance_id is not None else get_instance_id()

    payload_dict = {
        "license_id": license_id,
        "product": product,
        "environment": environment,
        "client_instance_id": inst_id,
        "request_id": request_id,
        "status": status,
        "lease_expires_at": exp.isoformat(),
        "server_time": st.isoformat(),
        "features": features or {"analysis": True, "export": True},
        "message": message,
    }

    message_bytes = canonical_payload(payload_dict)
    signed = signing_key.sign(message_bytes)
    sig_b64 = base64.b64encode(signed.signature).decode("ascii")

    full_response = dict(payload_dict)
    full_response["signature"] = sig_b64
    return full_response, sig_b64


# ── 1. Valid Signed Response ─────────────────────────────────────────


def test_1_valid_signed_response(test_keypair):
    """1. Valid signed response is accepted and parsed."""
    resp_dict, sig_b64 = make_signed_payload(
        test_keypair["signing_key"],
        status="active",
        license_id="TEST-LIC-001",
        product="alteryx-etl",
        environment="production",
        request_id="nonce-xyz",
    )
    assert verify_signature(resp_dict, sig_b64, test_keypair["public_b64"]) is True

    resp_obj = LicenseValidationResponse(**resp_dict)
    assert resp_obj.status == LicenseStatus.ACTIVE
    assert resp_obj.license_id == "TEST-LIC-001"
    assert resp_obj.product == "alteryx-etl"
    assert resp_obj.environment == "production"
    assert resp_obj.request_id == "nonce-xyz"


# ── 2. Invalid Signature ─────────────────────────────────────────────


def test_2_invalid_signature(test_keypair):
    """2. Invalid signature (tampered bytes) is rejected."""
    resp_dict, _ = make_signed_payload(test_keypair["signing_key"])
    corrupted_sig = base64.b64encode(b"X" * 64).decode("ascii")

    with pytest.raises(LicenseSignatureError, match="signature verification failed"):
        verify_signature(resp_dict, corrupted_sig, test_keypair["public_b64"])


# ── 3. Malformed Signature ───────────────────────────────────────────


def test_3_malformed_signature(test_keypair):
    """3. Malformed signature (non-base64 or invalid length) is rejected."""
    resp_dict, _ = make_signed_payload(test_keypair["signing_key"])

    # Non-base64 string
    with pytest.raises(LicenseSignatureError):
        verify_signature(resp_dict, "not-valid-base64!@#$", test_keypair["public_b64"])

    # Invalid length (e.g. 10 bytes instead of 64 bytes)
    short_sig = base64.b64encode(b"tooshort").decode("ascii")
    with pytest.raises(LicenseSignatureError):
        verify_signature(resp_dict, short_sig, test_keypair["public_b64"])


# ── 4. Wrong Public Key ──────────────────────────────────────────────


def test_4_wrong_public_key(test_keypair):
    """4. Wrong public key rejects the signature."""
    resp_dict, sig_b64 = make_signed_payload(test_keypair["signing_key"])

    # Unrelated keypair
    unrelated_key = SigningKey.generate()
    unrelated_pub_b64 = base64.b64encode(unrelated_key.verify_key.encode()).decode("ascii")

    with pytest.raises(LicenseSignatureError, match="signature verification failed"):
        verify_signature(resp_dict, sig_b64, unrelated_pub_b64)


# ── 5. Wrong License ID ──────────────────────────────────────────────


def test_5_wrong_license_id(test_keypair):
    """5. Response with wrong license ID is rejected."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="EXPECTED-CLIENT-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    # Server signs for DIFFERENT-CLIENT-002
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        license_id="DIFFERENT-CLIENT-002",
    )
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseInvalidError, match="License ID mismatch"):
            manager.validate_or_raise()


# ── 6. Wrong Product ─────────────────────────────────────────────────


def test_6_wrong_product(test_keypair):
    """6. Response with wrong product is rejected."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        product="alteryx-etl",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        license_id="TEST-LIC-001",
        product="other-product",
    )
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseInvalidError, match="Product mismatch"):
            manager.validate_or_raise()


# ── 7. Wrong Environment ─────────────────────────────────────────────


def test_7_wrong_environment(test_keypair):
    """7. Response with wrong environment is rejected."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        environment="production",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        license_id="TEST-LIC-001",
        environment="staging",
    )
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseInvalidError, match="Environment mismatch"):
            manager.validate_or_raise()


# ── 8. Wrong Request ID ──────────────────────────────────────────────


def test_8_wrong_request_id(test_keypair):
    """8. Response with wrong request_id nonce is rejected."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    # Server returns different request_id than sent
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        request_id="server-returned-different-nonce",
    )
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, "client-sent-original-nonce")):
        with pytest.raises(LicenseInvalidError, match="Protocol binding error: response request_id"):
            manager.validate_or_raise()


# ── 9. Missing Request ID ────────────────────────────────────────────


def test_9_missing_request_id():
    """9. Response missing request_id is rejected."""
    malformed_json = json.dumps({
        "license_id": "TEST-LIC-001",
        "product": "alteryx-etl",
        "status": "active",
        "lease_expires_at": datetime.now(timezone.utc).isoformat(),
        "server_time": datetime.now(timezone.utc).isoformat(),
        "signature": "sig",
    }).encode("utf-8")

    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64="dGVzdA==",
    )

    mock_resp = MagicMock()
    mock_resp.read.return_value = malformed_json
    mock_resp.__enter__.return_value = mock_resp

    with patch("backend.app.licensing.client.urlopen", return_value=mock_resp):
        from backend.app.licensing.client import validate_license
        with pytest.raises(LicenseInvalidError, match="missing required fields"):
            validate_license(config)


# ── 10. Expired Lease ────────────────────────────────────────────────


def test_10_expired_lease(test_keypair):
    """10. Expired lease from server is rejected."""
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        status="expired",
    )
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseExpiredError, match="expired"):
            manager.validate_or_raise()


# ── 11. Revoked License ──────────────────────────────────────────────


def test_11_revoked_license(test_keypair):
    """11. Revoked license from server is rejected."""
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        status="revoked",
    )
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseRevokedError, match="revoked"):
            manager.validate_or_raise()


# ── 12. Suspended License ────────────────────────────────────────────


def test_12_suspended_license(test_keypair):
    """12. Suspended license from server is rejected."""
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        status="suspended",
    )
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseExpiredError, match="suspended"):
            manager.validate_or_raise()


# ── 13. Startup with API Unavailable and No Previous Lease ───────────


def test_13_startup_with_api_unavailable_and_no_previous_lease(test_keypair):
    """13. Startup with API unavailable and no prior valid lease fails closed."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    with patch("backend.app.licensing.client.validate_license", side_effect=LicenseNetworkError("Connection refused")):
        with pytest.raises(LicenseExpiredError, match="unreachable and no valid lease exists"):
            manager.validate_or_raise()


# ── 14. Runtime API Outage Within Grace ──────────────────────────────


def test_14_runtime_api_outage_within_grace(test_keypair):
    """14. Runtime API outage within grace period allows application to continue."""
    now = datetime.now(timezone.utc)
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
        grace_seconds=72 * 3600,
    )
    manager = LicenseManager(config=config)

    # Establish an initial valid lease
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        status="active",
        lease_hours=24,
        server_time=now,
    )
    resp_obj = LicenseValidationResponse(**resp_dict)
    manager.lease.update_from_response(resp_obj)
    assert manager.is_licensed is True

    # Outage occurs
    manager.lease.record_failure()
    assert manager.lease.is_within_grace(config.grace_seconds) is True

    with patch("backend.app.licensing.client.validate_license", side_effect=LicenseNetworkError("Temporary outage")):
        # validate_or_raise should NOT raise because lease is within grace
        manager.validate_or_raise()
        assert manager.is_licensed is True


# ── 15. Runtime API Outage Beyond Grace ──────────────────────────────


def test_15_runtime_api_outage_beyond_grace(test_keypair):
    """15. Runtime API outage beyond grace period stops application."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
        grace_seconds=10,  # 10s grace
    )
    manager = LicenseManager(config=config)

    # Establish initial lease
    resp_dict, _ = make_signed_payload(test_keypair["signing_key"], status="active")
    resp_obj = LicenseValidationResponse(**resp_dict)
    manager.lease.update_from_response(resp_obj)

    # Outage started 60 seconds ago (exceeding 10s grace)
    manager.lease.outage_start_monotonic = manager.lease.last_successful_monotonic - 60.0

    assert manager.lease.is_within_grace(config.grace_seconds) is False

    with patch("backend.app.licensing.client.validate_license", side_effect=LicenseNetworkError("Offline")):
        with pytest.raises(LicenseExpiredError, match="unreachable and no valid lease exists"):
            manager.validate_or_raise()


# ── 16. Successful Heartbeat Renewal ─────────────────────────────────


def test_16_successful_heartbeat_renewal(test_keypair):
    """16. Successful heartbeat renewal extends the lease."""
    now = datetime.now(timezone.utc)
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    # Initial validation
    resp1_dict, _ = make_signed_payload(test_keypair["signing_key"], lease_hours=1, server_time=now)
    resp1_obj = LicenseValidationResponse(**resp1_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp1_dict, resp1_obj, resp1_dict["request_id"])):
        manager.validate_or_raise()
        assert manager.lease.valid is True
        initial_expiry = manager.lease.lease_expires_at

    # Renew with fresh 24h lease
    future_time = now + timedelta(minutes=45)
    resp2_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        lease_hours=24,
        server_time=future_time,
    )
    resp2_obj = LicenseValidationResponse(**resp2_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp2_dict, resp2_obj, resp2_dict["request_id"])):
        manager._perform_validation()
        assert manager.lease.valid is True
        assert manager.lease.lease_expires_at > initial_expiry


# ── 17. Failed Heartbeat Does Not Destroy Previous Valid Lease ───────


def test_17_failed_heartbeat_does_not_destroy_previously_valid_lease(test_keypair):
    """17. Failed heartbeat (transient network glitch) preserves existing valid lease."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
        grace_seconds=72 * 3600,
    )
    manager = LicenseManager(config=config)

    # Establish valid lease
    resp_dict, _ = make_signed_payload(test_keypair["signing_key"], status="active", lease_hours=24)
    resp_obj = LicenseValidationResponse(**resp_dict)
    manager.lease.update_from_response(resp_obj)
    original_expiry = manager.lease.lease_expires_at
    assert manager.lease.valid is True

    # Simulate network failure during validation
    with patch("backend.app.licensing.client.validate_license", side_effect=LicenseNetworkError("Connection timed out")):
        try:
            manager._perform_validation()
        except LicenseNetworkError:
            pass

    # The existing lease MUST remain valid and untampered
    assert manager.lease.valid is True
    assert manager.lease.lease_expires_at == original_expiry
    assert manager.lease.consecutive_failures == 1


# ── 18. Production Licensing Cannot Be Disabled With Env ─────────────


def test_18_production_licensing_cannot_be_disabled_with_env(monkeypatch):
    """18. ALTERYX_LICENSE_ENABLED=false does NOT disable production licensing."""
    monkeypatch.setenv("ALTERYX_LICENSE_ENABLED", "false")
    monkeypatch.setenv("ALTERYX_LICENSE_API_URL", "https://license.example.com")
    monkeypatch.setenv("ALTERYX_LICENSE_ID", "TEST-LIC-001")

    config = LicenseConfig.from_env()
    # Security requirement: production build licensing is permanently enabled
    assert config.enabled is True


# ── 19. Production Public Key Cannot Be Replaced Through Env ─────────


def test_19_production_public_key_cannot_be_replaced_through_env(monkeypatch):
    """19. ALTERYX_LICENSE_PUBLIC_KEY env var cannot override production key."""
    attacker_key = base64.b64encode(b"A" * 32).decode("ascii")
    monkeypatch.setenv("ALTERYX_LICENSE_PUBLIC_KEY", attacker_key)

    config = LicenseConfig.from_env()
    # Security requirement: env override must be ignored in production
    assert config.public_key_b64 != attacker_key


# ── 20. Canonicalization Is Deterministic ────────────────────────────


def test_20_canonicalization_is_deterministic():
    """20. Canonicalization produces identical sorted bytes regardless of input order and strips signature."""
    dict_a = {
        "signature": "do-not-include",
        "license_id": "ALT-001",
        "product": "alteryx-etl",
        "status": "active",
        "request_id": "nonce-1",
    }
    dict_b = {
        "request_id": "nonce-1",
        "status": "active",
        "product": "alteryx-etl",
        "license_id": "ALT-001",
        "signature": "different-sig-excluded",
    }

    canon_a = canonical_payload(dict_a)
    canon_b = canonical_payload(dict_b)

    assert canon_a == canon_b
    assert b"signature" not in canon_a


# ── 21. Signature Covers Request ID ──────────────────────────────────


def test_21_signature_covers_request_id(test_keypair):
    """21. Tampering with request_id invalidates the Ed25519 signature."""
    resp_dict, sig_b64 = make_signed_payload(
        test_keypair["signing_key"],
        request_id="original-nonce-12345",
    )

    # Tamper strictly with the request_id
    tampered_dict = dict(resp_dict)
    tampered_dict["request_id"] = "tampered-nonce-99999"

    with pytest.raises(LicenseSignatureError, match="signature verification failed"):
        verify_signature(tampered_dict, sig_b64, test_keypair["public_b64"])


# ── 22. License ID Mismatch After Valid Signature Is Rejected ────────


def test_22_license_id_mismatch_after_valid_signature_is_rejected(test_keypair):
    """22. Valid signature for tenant B is rejected when client is tenant A."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TENANT-A",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    # Validly signed response, but for TENANT-B
    resp_dict, sig_b64 = make_signed_payload(
        test_keypair["signing_key"],
        license_id="TENANT-B",
    )
    # The signature itself is cryptographically valid
    assert verify_signature(resp_dict, sig_b64, test_keypair["public_b64"]) is True

    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"])):
        with pytest.raises(LicenseInvalidError, match="License ID mismatch"):
            manager.validate_or_raise()


# ── Shutdown Cleanliness ─────────────────────────────────────────────


def test_shutdown_terminates_cleanly():
    """Background licensing task terminates cleanly on shutdown."""
    import asyncio

    async def _async_test():
        config = LicenseConfig(
            enabled=True,
            api_url="https://license.example.com",
            license_id="TEST-LIC-001",
            public_key_b64="dGVzdA==",
            heartbeat_seconds=3600,
        )
        manager = LicenseManager(config=config)

        await manager.start_renewal_loop()
        assert manager._renewal_task is not None
        assert not manager._renewal_task.done()

        await manager.stop_renewal_loop()
        assert manager._renewal_task is None
        assert manager._shutdown_event.is_set()

    asyncio.run(_async_test())


# ── 23. Runtime Invalid License Response Shuts Down Without Grace ────


def test_23_runtime_invalid_license_response_shuts_down_immediately_without_grace(test_keypair):
    """23. Runtime heartbeat receiving an invalid license response shuts down immediately without entering grace."""
    import asyncio

    shutdown_reasons: list[str] = []

    def mock_shutdown(reason: str):
        shutdown_reasons.append(reason)

    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="EXPECTED-TENANT-001",
        public_key_b64=test_keypair["public_b64"],
        heartbeat_seconds=1,
        grace_seconds=72 * 3600,
    )
    manager = LicenseManager(config=config, on_shutdown=mock_shutdown)

    # Establish an initial valid lease
    now = datetime.now(timezone.utc)
    resp1_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        license_id="EXPECTED-TENANT-001",
        status="active",
        lease_hours=24,
        server_time=now,
    )
    resp1_obj = LicenseValidationResponse(**resp1_dict)
    manager.lease.update_from_response(resp1_obj)
    assert manager.is_licensed is True

    # Server returns a response signed for DIFFERENT-TENANT-999
    resp2_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        license_id="DIFFERENT-TENANT-999",
        status="active",
        lease_hours=24,
        server_time=now,
    )
    resp2_obj = LicenseValidationResponse(**resp2_dict)

    async def _run_heartbeat():
        with patch("backend.app.licensing.client.validate_license", return_value=(resp2_dict, resp2_obj, resp2_dict["request_id"], get_instance_id())):
            await manager.start_renewal_loop()
            await asyncio.sleep(1.2)
            await manager.stop_renewal_loop()

    asyncio.run(_run_heartbeat())

    # Must shut down immediately without entering grace
    assert len(shutdown_reasons) == 1
    assert "License ID mismatch" in shutdown_reasons[0]
    assert manager.lease.valid is False
    assert manager.is_licensed is False


# ── 24. Client Instance Mismatch Rejected ────────────────────────────


def test_24_client_instance_mismatch_rejected(test_keypair):
    """24. Response with client_instance_id differing from requested instance ID is rejected."""
    config = LicenseConfig(
        enabled=True,
        api_url="https://license.example.com",
        license_id="TEST-LIC-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config)

    # Server signs with a DIFFERENT client_instance_id
    resp_dict, _ = make_signed_payload(
        test_keypair["signing_key"],
        client_instance_id="different-unauthorized-instance",
    )
    resp_obj = LicenseValidationResponse(**resp_dict)

    with patch("backend.app.licensing.client.validate_license", return_value=(resp_dict, resp_obj, resp_dict["request_id"], "expected-request-instance")):
        with pytest.raises(LicenseInvalidError, match="Client instance mismatch"):
            manager.validate_or_raise()

