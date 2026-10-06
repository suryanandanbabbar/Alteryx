"""Comprehensive production tests for the Databricks Key Vault-backed Ed25519 licensing subsystem.

Test requirements coverage:
 1. Valid signed license artifact validates and enables features.
 2. Tampered signature bytes fail closed.
 3. Modified license_id fails closed.
 4. Modified product fails closed.
 5. Modified environment fails closed.
 6. Modified expires_at fails closed.
 7. Expired license fails closed.
 8. Malformed JSON fails closed.
 9. Missing signature fails closed.
10. Invalid base64 signature fails closed.
11. Missing required field fails closed.
12. Wrong field type fails closed.
13. Invalid feature type (non-boolean) fails closed.
14. Empty secret fails closed.
15. Secret provider failure fails closed.
16. Wrong public key fails closed.
17. Exact expiration boundary: now == expires_at => expired.
18. Future valid expiration: now < expires_at => valid.
19. Embedded public key cannot be overridden through environment.
20. Licensing cannot be disabled through environment.
21. Identity mismatches fail closed.
22. Databricks provider error handling.
23. Timezone-naive issued_at is strictly rejected.
24. Timezone-naive expires_at is strictly rejected.
25. Non-UTC timezone offsets are strictly rejected.
26. Canonical UTC timestamps with 'Z' are accepted.
27. Expiration boundary triad: now < exp (valid), now == exp (expired), now > exp (expired).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from nacl.signing import SigningKey

from backend.app.licensing.config import LicenseConfig, _EMBEDDED_PUBLIC_KEY
from backend.app.licensing.errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseSecretError,
    LicenseSignatureError,
)
from backend.app.licensing.manager import LicenseManager
from backend.app.licensing.models import LicenseArtifact, LicenseState
from backend.app.licensing.secret_provider import DatabricksSecretProvider, InMemorySecretProvider
from backend.app.licensing.verifier import canonical_payload, validate_expiry, verify_signature


# ── Test Fixtures & Helpers ──────────────────────────────────────────


@pytest.fixture
def test_keypair():
    """Generate an ephemeral Ed25519 keypair strictly for testing."""
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    pub_b64 = base64.b64encode(verify_key.encode()).decode("ascii")
    return {
        "signing_key": signing_key,
        "verify_key": verify_key,
        "public_b64": pub_b64,
    }


def make_signed_artifact(
    signing_key: SigningKey,
    *,
    license_id: str = "CLIENT-ALTERYX-001",
    product: str = "alteryx-etl",
    environment: str = "production",
    issued_at: str = "2026-10-06T00:00:00Z",
    expires_at: str | None = None,
    features: dict | None = None,
) -> tuple[dict, str]:
    """Helper to construct a valid signed license artifact using canonicalization."""
    if expires_at is None:
        future = datetime.now(timezone.utc) + timedelta(days=30)
        expires_at = future.strftime("%Y-%m-%dT%H:%M:%SZ")

    if features is None:
        features = {
            "workflow_analysis": True,
            "portfolio_rationalisation": True,
            "python_translation": True,
            "export_reports": True,
        }

    payload_dict = {
        "license_id": license_id,
        "product": product,
        "environment": environment,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "features": features,
    }

    canon_bytes = canonical_payload(payload_dict)
    sig_raw = signing_key.sign(canon_bytes).signature
    sig_b64 = base64.b64encode(sig_raw).decode("ascii")

    artifact_dict = dict(payload_dict)
    artifact_dict["signature"] = sig_b64
    artifact_json = json.dumps(artifact_dict)

    return artifact_dict, artifact_json


# ── 1. Valid Signed License ───────────────────────────────────────────


def test_1_valid_signed_license(test_keypair):
    """1. Valid signed license artifact validates successfully and enables features."""
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"])

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    manager.validate_or_raise()

    assert manager.is_licensed is True
    assert manager.state.is_valid is True
    assert manager.state.license_id == "CLIENT-ALTERYX-001"
    assert manager.state.product == "alteryx-etl"
    assert manager.state.environment == "production"
    assert manager.has_feature("workflow_analysis") is True
    assert manager.has_feature("portfolio_rationalisation") is True
    assert manager.has_feature("python_translation") is True
    assert manager.has_feature("export_reports") is True
    assert manager.has_feature("nonexistent_feature") is False


# ── 2. Invalid Signature ──────────────────────────────────────────────


def test_2_invalid_signature(test_keypair):
    """2. Tampered signature bytes cause LicenseSignatureError and fail closed."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])

    sig_bytes = bytearray(base64.b64decode(artifact_dict["signature"]))
    sig_bytes[0] ^= 0xFF
    artifact_dict["signature"] = base64.b64encode(sig_bytes).decode("ascii")

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 3. Modified License ID ────────────────────────────────────────────


def test_3_modified_license_id(test_keypair):
    """3. Changing license_id invalidates cryptographic signature."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["license_id"] = "TAMPERED-ID"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 4. Modified Product ───────────────────────────────────────────────


def test_4_modified_product(test_keypair):
    """4. Changing product invalidates cryptographic signature."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["product"] = "alteryx-other"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 5. Modified Environment ───────────────────────────────────────────


def test_5_modified_environment(test_keypair):
    """5. Changing environment invalidates cryptographic signature."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["environment"] = "development"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 6. Modified Expires At ────────────────────────────────────────────


def test_6_modified_expires_at(test_keypair):
    """6. Tampering with expires_at invalidates cryptographic signature."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["expires_at"] = "2099-12-31T23:59:59Z"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 7. Expired License ────────────────────────────────────────────────


def test_7_expired_license(test_keypair):
    """7. Validly signed license with an expired timestamp fails closed."""
    past_date = "2020-01-01T00:00:00Z"
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2019-01-01T00:00:00Z",
        expires_at=past_date,
    )

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseExpiredError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 8. Malformed JSON ─────────────────────────────────────────────────


def test_8_malformed_json(test_keypair):
    """8. Malformed JSON raises LicenseInvalidError."""
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): "{invalid json: true,"
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 9. Missing Signature ──────────────────────────────────────────────


def test_9_missing_signature(test_keypair):
    """9. Missing signature field raises LicenseInvalidError."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    del artifact_dict["signature"]

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 10. Invalid Base64 Signature ──────────────────────────────────────


def test_10_invalid_base64_signature(test_keypair):
    """10. Malformed base64 signature raises LicenseSignatureError."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["signature"] = "NOT_VALID_BASE64!!!"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 11. Missing Required Field ────────────────────────────────────────


def test_11_missing_required_field(test_keypair):
    """11. Missing required field raises LicenseInvalidError."""
    for field in ["license_id", "product", "environment", "issued_at", "expires_at", "features"]:
        artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
        del artifact_dict[field]

        provider = InMemorySecretProvider({
            ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
        })
        config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
        manager = LicenseManager(config=config, secret_provider=provider)

        with pytest.raises(LicenseInvalidError):
            manager.validate_or_raise()


# ── 12. Wrong Field Type ──────────────────────────────────────────────


def test_12_wrong_field_type(test_keypair):
    """12. Integer product or non-string license_id raises LicenseInvalidError."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    artifact_dict["product"] = 12345

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError):
        manager.validate_or_raise()


# ── 13. Invalid Feature Type ──────────────────────────────────────────


def test_13_invalid_feature_type(test_keypair):
    """13. Non-boolean feature value raises LicenseInvalidError."""
    artifact_dict, _ = make_signed_artifact(test_keypair["signing_key"])
    # String, not StrictBool
    artifact_dict["features"]["workflow_analysis"] = "true"

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError):
        manager.validate_or_raise()


# ── 14. Empty Secret ──────────────────────────────────────────────────


def test_14_empty_secret(test_keypair):
    """14. Empty secret string raises LicenseSecretError."""
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): "   "
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSecretError):
        manager.validate_or_raise()


# ── 15. Secret Provider Failure ───────────────────────────────────────


def test_15_secret_provider_failure(test_keypair):
    """15. Secret lookup failure raises LicenseSecretError."""
    provider = InMemorySecretProvider()  # Empty provider
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSecretError):
        manager.validate_or_raise()


# ── 16. Wrong Public Key ──────────────────────────────────────────────


def test_16_wrong_public_key(test_keypair):
    """16. Verification with a different public key raises LicenseSignatureError."""
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"])

    attacker_key = SigningKey.generate().verify_key
    attacker_pub_b64 = base64.b64encode(attacker_key.encode()).decode("ascii")

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=attacker_pub_b64)
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSignatureError):
        manager.validate_or_raise()


# ── 17. Exact Expiration Boundary ─────────────────────────────────────


def test_17_exact_expiration_boundary(test_keypair):
    """17. When now == expires_at, license is expired (boundary condition)."""
    fixed_time = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)

    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00Z",
        expires_at=fixed_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_time
        with pytest.raises(LicenseExpiredError):
            manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 18. Future Valid Expiration ───────────────────────────────────────


def test_18_future_valid_expiration(test_keypair):
    """18. When now < expires_at, license is active and valid."""
    fixed_now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)
    fixed_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)

    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00Z",
        expires_at=fixed_exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        manager.validate_or_raise()

    assert manager.is_licensed is True
    assert manager.state.is_valid is True


# ── 19. Embedded Public Key Cannot Be Overridden ──────────────────────


def test_19_embedded_public_key_cannot_be_overridden_by_env(monkeypatch):
    """19. ALTERYX_LICENSE_PUBLIC_KEY cannot override embedded production key."""
    attacker_key = base64.b64encode(b"C" * 32).decode("ascii")
    monkeypatch.setenv("ALTERYX_LICENSE_PUBLIC_KEY", attacker_key)

    config = LicenseConfig.from_env()
    assert config.public_key_b64 == _EMBEDDED_PUBLIC_KEY
    assert config.public_key_b64 != attacker_key


# ── 20. Licensing Cannot Be Disabled Through Environment ──────────────


def test_20_licensing_cannot_be_disabled_through_env(monkeypatch):
    """20. ALTERYX_LICENSE_ENABLED=false does NOT disable licensing."""
    monkeypatch.setenv("ALTERYX_LICENSE_ENABLED", "false")

    config = LicenseConfig.from_env()
    assert config.enabled is True

    provider = InMemorySecretProvider()
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseSecretError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 21. Identity Mismatch Fails Closed (ID, Product, Environment) ──────


def test_21_identity_mismatches_fail_closed(test_keypair):
    """21. Validly signed license with wrong expected identity fails closed."""
    # 1. License ID mismatch
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        license_id="DIFFERENT-TENANT-999",
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(
        license_id="CLIENT-ALTERYX-001",
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError, match="License ID mismatch"):
        manager.validate_or_raise()

    # 2. Product mismatch
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        product="unauthorized-product",
    )
    provider.set_secret("alteryx-licenseArtifacts",
                        "alteryx-license", artifact_json)
    with pytest.raises(LicenseInvalidError, match="Product mismatch"):
        manager.validate_or_raise()

    # 3. Environment mismatch
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        environment="staging",
    )
    provider.set_secret("alteryx-licenseArtifacts",
                        "alteryx-license", artifact_json)
    with pytest.raises(LicenseInvalidError, match="Environment mismatch"):
        manager.validate_or_raise()


# ── 22. Databricks Provider Error Handling ────────────────────────────


def test_22_databricks_provider_resolution_and_error_handling():
    """22. DatabricksSecretProvider raises LicenseSecretError when dbutils is missing or fails."""
    provider_no_dbutils = DatabricksSecretProvider(dbutils=None)
    with pytest.raises(LicenseSecretError, match="dbutils is not available"):
        provider_no_dbutils.get_secret("scope", "key")

    mock_dbutils = MagicMock()
    mock_dbutils.secrets.get.side_effect = RuntimeError(
        "KeyVault access denied")
    provider_mock = DatabricksSecretProvider(dbutils=mock_dbutils)

    with pytest.raises(LicenseSecretError, match="Failed to retrieve secret"):
        provider_mock.get_secret("scope", "key")

    mock_dbutils.secrets.get.side_effect = None
    mock_dbutils.secrets.get.return_value = "   "
    with pytest.raises(LicenseSecretError, match="empty"):
        provider_mock.get_secret("scope", "key")


# ── 23. Timezone-naive issued_at Rejected ─────────────────────────────


def test_23_timezone_naive_issued_at_rejected(test_keypair):
    """23. Timezone-naive issued_at string must fail closed with LicenseInvalidError."""
    artifact_dict, _ = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00",  # Missing 'Z' / timezone offset
    )

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError, match="timezone-aware"):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 24. Timezone-naive expires_at Rejected ────────────────────────────


def test_24_timezone_naive_expires_at_rejected(test_keypair):
    """24. Timezone-naive expires_at string must fail closed with LicenseInvalidError."""
    artifact_dict, _ = make_signed_artifact(
        test_keypair["signing_key"],
        expires_at="2026-10-07T00:00:00",  # Missing 'Z' / timezone offset
    )

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError, match="timezone-aware"):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 25. Non-UTC Timezone Offsets Rejected ─────────────────────────────


def test_25_non_utc_timezone_offsets_rejected(test_keypair):
    """25. Non-UTC timezone offsets (e.g. +05:30 or -04:00) must fail closed."""
    # Test non-UTC issued_at (+05:30)
    artifact_dict, _ = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T05:30:00+05:30",
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): json.dumps(artifact_dict)
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError, match="non-UTC offset"):
        manager.validate_or_raise()

    # Test non-UTC expires_at (-04:00)
    artifact_dict_exp, _ = make_signed_artifact(
        test_keypair["signing_key"],
        expires_at="2026-10-07T04:00:00-04:00",
    )
    provider.set_secret("alteryx-licenseArtifacts",
                        "alteryx-license", json.dumps(artifact_dict_exp))
    with pytest.raises(LicenseInvalidError, match="non-UTC offset"):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 26. Canonical UTC Timestamps Accepted ─────────────────────────────


def test_26_canonical_utc_z_accepted(test_keypair):
    """26. Canonical UTC format ending in 'Z' (and zero offset +00:00) validates successfully."""
    fixed_now = datetime(2026, 10, 6, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Standard canonical 'Z' representation
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00Z",
        expires_at="2026-10-07T00:00:00Z",
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        manager.validate_or_raise()

    assert manager.is_licensed is True

    # 2. Explicit +00:00 UTC offset representation
    artifact_dict_plus0, artifact_json_plus0 = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00+00:00",
        expires_at="2026-10-07T00:00:00+00:00",
    )
    provider.set_secret("alteryx-licenseArtifacts",
                        "alteryx-license", artifact_json_plus0)
    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        manager.validate_or_raise()

    assert manager.is_licensed is True


# ── 27. Expiration Boundary Triad ─────────────────────────────────────


def test_27_expiration_boundary_triad(test_keypair):
    """27. Triad verification: now < exp is valid, now == exp is expired, now > exp is expired."""
    fixed_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2026-10-06T00:00:00Z",
        expires_at="2026-10-07T00:00:00Z",
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    # Condition 1: now < exp -> valid
    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_exp - timedelta(seconds=1)
        manager.validate_or_raise()
        assert manager.is_licensed is True

    # Condition 2: now == exp -> expired (fails closed)
    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_exp
        with pytest.raises(LicenseExpiredError):
            manager.validate_or_raise()
        assert manager.is_licensed is False

    # Condition 3: now > exp -> expired (fails closed)
    with patch("backend.app.licensing.verifier.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_exp + timedelta(seconds=1)
        with pytest.raises(LicenseExpiredError):
            manager.validate_or_raise()
        assert manager.is_licensed is False


# ── 28. validate_expiry Rejects Naive Datetime Directly ───────────────


def test_28_validate_expiry_rejects_naive_datetime_directly():
    """28. Naive datetime passed directly to validate_expiry is rejected with LicenseInvalidError."""
    # 1. Naive expires_at
    naive_exp = datetime(2026, 10, 7, 0, 0, 0)
    with pytest.raises(LicenseInvalidError, match="naive datetime rejected"):
        validate_expiry(naive_exp)

    # 2. Naive current_time
    aware_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
    naive_now = datetime(2026, 10, 6, 0, 0, 0)
    with pytest.raises(LicenseInvalidError, match="naive datetime rejected"):
        validate_expiry(aware_exp, current_time=naive_now)


# ── 29. validate_expiry Rejects Non-UTC Datetime Directly ─────────────


def test_29_validate_expiry_rejects_non_utc_datetime_directly():
    """29. Non-UTC datetime passed directly to validate_expiry is rejected with LicenseInvalidError."""
    # 1. Non-UTC expires_at (+05:30)
    non_utc_tz = timezone(timedelta(hours=5, minutes=30))
    non_utc_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=non_utc_tz)
    with pytest.raises(LicenseInvalidError, match="non-UTC offset"):
        validate_expiry(non_utc_exp)

    # 2. Non-UTC current_time (-04:00)
    aware_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
    non_utc_now = datetime(2026, 10, 6, 0, 0, 0,
                           tzinfo=timezone(timedelta(hours=-4)))
    with pytest.raises(LicenseInvalidError, match="non-UTC offset"):
        validate_expiry(aware_exp, current_time=non_utc_now)


# ── 30. validate_expiry Accepts Valid UTC Datetime Directly ───────────


def test_30_validate_expiry_accepts_utc_datetime_directly():
    """30. Valid UTC datetime passed directly to validate_expiry is accepted when now < expires_at."""
    aware_exp = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
    aware_now = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
    # Valid call should execute without raising any exception
    validate_expiry(aware_exp, current_time=aware_now)


# ── 31. Environment-Variable Identity Override Attempt Fails ──────────


def test_31_environment_variable_identity_override_attempt_fails(monkeypatch, test_keypair):
    """31. Customer environment variables cannot override immutable production identity."""
    monkeypatch.setenv("ALTERYX_LICENSE_ID", "UNAUTHORIZED-TENANT")
    monkeypatch.setenv("ALTERYX_LICENSE_PRODUCT", "unauthorized-product")
    monkeypatch.setenv("ALTERYX_LICENSE_ENVIRONMENT", "staging")

    config = LicenseConfig.from_env()
    assert config.license_id == "CLIENT-ALTERYX-001"
    assert config.product == "alteryx-etl"
    assert config.environment == "production"

    # Even if an unauthorized artifact is retrieved, verification against production identity rejects it
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        license_id="UNAUTHORIZED-TENANT",
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    manager = LicenseManager(
        config=LicenseConfig(public_key_b64=test_keypair["public_b64"]),
        secret_provider=provider,
    )
    with pytest.raises(LicenseInvalidError, match="License ID mismatch"):
        manager.validate_or_raise()


# ── 32. License-Disable Environment Variables Ineffective ─────────────


def test_32_license_disable_environment_variables_ineffective(monkeypatch):
    """32. LICENSE_ENABLED=false and ALTERYX_DISABLE_LICENSE=true cannot bypass validation."""
    monkeypatch.setenv("LICENSE_ENABLED", "false")
    monkeypatch.setenv("ALTERYX_DISABLE_LICENSE", "true")
    monkeypatch.setenv("ALTERYX_LICENSE_ENABLED", "false")

    config = LicenseConfig.from_env()
    assert config.enabled is True

    # Validation still fails closed if secret is missing or invalid
    provider = InMemorySecretProvider()
    manager = LicenseManager(config=config, secret_provider=provider)
    with pytest.raises(LicenseSecretError):
        manager.validate_or_raise()

    assert manager.is_licensed is False


# ── 33. Secret Scope and Name Override Attempt Fails ──────────────────


def test_33_secret_scope_and_name_override_attempt_fails(monkeypatch):
    """33. Customer environment variables cannot redirect production secret scope or name."""
    monkeypatch.setenv("ALTERYX_LICENSE_SECRET_SCOPE", "attacker-custom-scope")
    monkeypatch.setenv("ALTERYX_LICENSE_SECRET_NAME", "attacker-custom-secret")

    config = LicenseConfig.from_env()
    assert config.secret_scope == "alteryx-licenseArtifacts"
    assert config.secret_name == "alteryx-license"
