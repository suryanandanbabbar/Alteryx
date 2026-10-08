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
    LicenseLimitExceededError,
    LicenseSecretError,
    LicenseSignatureError,
)
from backend.app.licensing.manager import LicenseManager
from backend.app.licensing.models import LicenseArtifact, LicenseState
from backend.app.licensing.secret_provider import DatabricksSecretProvider, InMemorySecretProvider
from backend.app.licensing.usage_source import CallableUsageDataSource, InMemoryUsageDataSource, UsageDataSource
from backend.app.licensing.developer_config import DeveloperLicenseConfig
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
    policy: dict | None = None,
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
    if policy is None:
        policy = {
            "date": {"enabled": True},
            "volume": {"enabled": False, "limit": 0},
            "token_usage": {"enabled": False, "limit": 0},
        }
    payload_dict["policy"] = policy

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


# ── 34. All 8 Criteria Combinations ───────────────────────────────────


def test_34_criteria_combinations_validation(test_keypair):
    """34. Criteria combinations: local 0/0/0 accepted at config time; 7 valid artifact combinations pass."""
    # Local 0/0/0 does not fail config validation (local flags do not control runtime enforcement)
    config_000 = LicenseConfig(
        date_enabled=0,
        volume_enabled=0,
        token_usage_enabled=0,
        public_key_b64=test_keypair["public_b64"],
    )
    config_000.validate()

    valid_combinations = [
        (0, 0, 1),
        (0, 1, 0),
        (0, 1, 1),
        (1, 0, 0),
        (1, 0, 1),
        (1, 1, 0),
        (1, 1, 1),
    ]

    vol_source = InMemoryUsageDataSource(usage=50)
    tok_source = InMemoryUsageDataSource(usage=200)

    for d_en, v_en, t_en in valid_combinations:
        cfg = LicenseConfig(
            date_enabled=d_en,
            volume_enabled=v_en,
            token_usage_enabled=t_en,
            volume_limit=100 if v_en else 0,
            token_usage_limit=500 if t_en else 0,
            volume_usage_source=vol_source if v_en else None,
            token_usage_source=tok_source if t_en else None,
            public_key_b64=test_keypair["public_b64"],
        )
        cfg.validate()

        policy = {
            "date": {"enabled": bool(d_en)},
            "volume": {"enabled": bool(v_en), "limit": 100},
            "token_usage": {"enabled": bool(t_en), "limit": 500},
        }

        artifact_dict, artifact_json = make_signed_artifact(
            test_keypair["signing_key"],
            policy=policy,
        )
        provider = InMemorySecretProvider({
            ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
        })
        manager = LicenseManager(config=cfg, secret_provider=provider)
        manager.validate_or_raise()
        assert manager.is_licensed is True


# ── 35. Volume Boundary Conditions ────────────────────────────────────


def test_35_volume_boundary_conditions(test_keypair):
    """35. Volume boundary: 99/100 passes, 100/100 fails, 101/100 fails."""
    vol_source = InMemoryUsageDataSource(usage=99)
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })

    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,
        volume_limit=100,
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=cfg, secret_provider=provider)

    # 1. current = 99 -> pass
    manager.validate_or_raise()
    assert manager.is_licensed is True
    assert manager.volume_state.current == 99

    # 2. current = 100 -> fail closed
    vol_source.set_usage(100)
    with pytest.raises(LicenseLimitExceededError) as exc_info:
        manager.validate_or_raise()
    assert exc_info.value.criterion == "volume"
    assert exc_info.value.current == 100
    assert exc_info.value.limit == 100

    # 3. current = 101 -> fail closed
    vol_source.set_usage(101)
    with pytest.raises(LicenseLimitExceededError) as exc_info:
        manager.validate_or_raise()
    assert exc_info.value.current == 101


# ── 36. Token Usage Boundary Conditions ───────────────────────────────


def test_36_token_usage_boundary_conditions(test_keypair):
    """36. Token usage boundary: 999/1000 passes, 1000/1000 fails, 1001/1000 fails."""
    tok_source = InMemoryUsageDataSource(usage=999)
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 1000},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })

    cfg = LicenseConfig(
        date_enabled=1,
        token_usage_enabled=1,
        token_usage_limit=1000,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=cfg, secret_provider=provider)

    # 1. current = 999 -> pass
    manager.validate_or_raise()
    assert manager.is_licensed is True
    assert manager.token_state.current == 999

    # 2. current = 1000 -> fail closed
    tok_source.set_usage(1000)
    with pytest.raises(LicenseLimitExceededError) as exc_info:
        manager.validate_or_raise()
    assert exc_info.value.criterion == "token_usage"
    assert exc_info.value.current == 1000
    assert exc_info.value.limit == 1000

    # 3. current = 1001 -> fail closed
    tok_source.set_usage(1001)
    with pytest.raises(LicenseLimitExceededError) as exc_info:
        manager.validate_or_raise()
    assert exc_info.value.current == 1001


# ── 37. Policy Tampering Invalidates Ed25519 Signature ─────────────────


def test_37_policy_tampering_invalidates_signature(test_keypair):
    """37. Tampering with policy limits or flags invalidates canonical Ed25519 signature."""
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )

    # Client tampers with the volume limit from 100 to 1000000
    tampered_dict = json.loads(artifact_json)
    tampered_dict["policy"]["volume"]["limit"] = 1000000
    tampered_json = json.dumps(tampered_dict)

    vol_source = InMemoryUsageDataSource(usage=50)
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): tampered_json
    })
    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,
        volume_limit=100,
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=cfg, secret_provider=provider)

    with pytest.raises(LicenseSignatureError, match="verification failed"):
        manager.validate_or_raise()


# ── 38. Disabled Criteria Bypass Source Queries ───────────────────────


def test_38_disabled_criteria_bypasses_source(test_keypair):
    """38. Disabled criteria never queries usage source, even if source is None."""
    mock_source = MagicMock()
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })

    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=0,
        token_usage_enabled=0,
        volume_usage_source=mock_source,
        token_usage_source=mock_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=cfg, secret_provider=provider)
    manager.validate_or_raise()

    assert manager.is_licensed is True
    # Verify mock was never called
    mock_source.get_current_usage.assert_not_called()


# ── 39. Usage Source Failures Fail Closed ─────────────────────────────


def test_39_usage_source_failures_fail_closed(test_keypair):
    """39. Usage source exceptions, negative usage, or invalid types fail closed."""
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })

    # 1. Exception in source
    faulty_source = MagicMock()
    faulty_source.get_current_usage.side_effect = RuntimeError("Database down")
    cfg_fault = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,
        volume_limit=100,
        volume_usage_source=faulty_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg_fault, secret_provider=provider)
    with pytest.raises(LicenseInvalidError, match="Failed to retrieve current volume usage"):
        mgr.validate_or_raise()

    # 2. Negative usage returned
    faulty_source.side_effect = None
    faulty_source.get_current_usage.side_effect = None
    faulty_source.get_current_usage.return_value = -5
    with pytest.raises(LicenseInvalidError, match="invalid usage: -5"):
        mgr.validate_or_raise()

    # 3. Non-integer returned
    faulty_source.get_current_usage.return_value = "not_an_int"
    with pytest.raises(LicenseInvalidError, match="invalid usage"):
        mgr.validate_or_raise()


# ── 40. Developer Configuration Model & Unsigned Artifact ─────────────


def test_40_developer_config_model_and_artifact_generation(tmp_path):
    """40. DeveloperLicenseConfig validation, unsigned artifact generation, file persistence."""
    dev_config = DeveloperLicenseConfig.load_from_file()
    dev_config.enforcement.date_enabled = 1
    dev_config.enforcement.volume_enabled = 1
    dev_config.volume.volume_limit = 2500

    payload = dev_config.generate_unsigned_artifact_payload()
    assert payload["license_id"] == "CLIENT-ALTERYX-001"
    assert payload["policy"]["volume"]["enabled"] is True
    assert payload["policy"]["volume"]["limit"] == 2500
    assert payload["policy"]["token_usage"]["enabled"] is False

    # Persistence roundtrip to temporary path
    conf_path = tmp_path / "test_config.json"
    dev_config.save_to_file(conf_path)
    loaded = DeveloperLicenseConfig.load_from_file(conf_path)
    assert loaded.volume.volume_limit == 2500


# ── 41. Package Portability & CWD Independence ────────────────────────


def test_41_package_portability_and_cwd_independence(monkeypatch, tmp_path):
    """41. Package resolves developer_config.json relative to itself regardless of process CWD."""
    # Change current working directory to a completely different temp directory
    monkeypatch.chdir(tmp_path)

    # 1. DeveloperLicenseConfig loads correctly from package path
    dev_cfg = DeveloperLicenseConfig.load_from_file()
    assert dev_cfg.identity.license_id == "CLIENT-ALTERYX-001"
    assert dev_cfg.artifact_secret.secret_scope == "alteryx-licenseArtifacts"

    # 2. LicenseConfig loads correctly without depending on CWD
    lic_cfg = LicenseConfig.load()
    assert lic_cfg.license_id == "CLIENT-ALTERYX-001"
    assert lic_cfg.secret_scope == "alteryx-licenseArtifacts"
    assert lic_cfg.secret_name == "alteryx-license"

    # 3. LicenseManager instantiates and reads package config
    mgr = LicenseManager(config=lic_cfg)
    assert mgr.config.license_id == "CLIENT-ALTERYX-001"


# ── 42. Artifact Without Policy Rejected ──────────────────────────────


def test_42_artifact_without_policy_rejected(test_keypair):
    """42. New-format license artifact without required policy fails schema validation."""
    # Construct an artifact missing the policy field
    payload_dict = {
        "license_id": "CLIENT-ALTERYX-001",
        "product": "alteryx-etl",
        "environment": "production",
        "issued_at": "2026-10-06T00:00:00Z",
        "expires_at": "2026-11-06T00:00:00Z",
        "features": {
            "workflow_analysis": True,
            "portfolio_rationalisation": True,
            "python_translation": True,
            "export_reports": True,
        },
        # No "policy" key!
    }
    canon_bytes = canonical_payload(payload_dict)
    sig_raw = test_keypair["signing_key"].sign(canon_bytes).signature
    sig_b64 = base64.b64encode(sig_raw).decode("ascii")

    artifact_dict = dict(payload_dict)
    artifact_dict["signature"] = sig_b64
    artifact_json = json.dumps(artifact_dict)

    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })
    config = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    manager = LicenseManager(config=config, secret_provider=provider)

    with pytest.raises(LicenseInvalidError, match="policy"):
        manager.validate_or_raise()


# ── 43. Signed Artifact Policy Is Sole Authority ─────────────────────


def test_43_signed_artifact_policy_is_sole_authority(test_keypair):
    """43. Runtime policy is strictly dictated by the signed artifact policy (no local config OR merge)."""
    # 1. Signed artifact has volume=False. Even if local config had volume enabled, runtime does NOT query source!
    mock_volume_source = MagicMock()
    policy_no_vol = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy_no_vol,
    )
    provider = InMemorySecretProvider({
        ("alteryx-licenseArtifacts", "alteryx-license"): artifact_json
    })

    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,  # Local config says 1, but signed artifact says False!
        volume_limit=10,
        volume_usage_source=mock_volume_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager = LicenseManager(config=cfg, secret_provider=provider)
    manager.validate_or_raise()

    assert manager.is_licensed is True
    # Volume source was NOT queried because signed artifact disabled volume
    mock_volume_source.get_current_usage.assert_not_called()
    assert manager.volume_state.enabled is False

    # 2. Signed artifact has volume=True with limit=50.
    # Even if local config had volume_limit=999, the signed limit 50 is enforced!
    policy_with_vol = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 50},
        "token_usage": {"enabled": False, "limit": 0},
    }
    artifact_dict2, artifact_json2 = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy_with_vol,
    )
    provider.set_secret("alteryx-licenseArtifacts", "alteryx-license", artifact_json2)

    vol_source = InMemoryUsageDataSource(usage=50)  # Current usage equals signed limit 50!
    cfg2 = LicenseConfig(
        date_enabled=1,
        volume_enabled=0,  # Local config says 0, but signed artifact says True!
        volume_limit=999,  # Local limit says 999
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    manager2 = LicenseManager(config=cfg2, secret_provider=provider)

    # Must fail because signed artifact requires volume check and limit is 50, and current is 50!
    with pytest.raises(LicenseLimitExceededError) as exc_info:
        manager2.validate_or_raise()
    assert exc_info.value.limit == 50
    assert exc_info.value.current == 50


# ── 44. Databricks Adapter Dynamic Scope and Key ──────────────────────


def test_44_databricks_adapter_dynamic_scope_and_key():
    """44. Databricks adapter dynamically retrieves arbitrary scope and key without hardcoding."""
    from backend.app.licensing.adapters.databricks import DatabricksSecretProvider

    mock_dbutils = MagicMock()
    mock_dbutils.secrets.get.return_value = '{"some": "secret"}'

    provider = DatabricksSecretProvider(dbutils=mock_dbutils)
    secret = provider.get_secret("custom-tenant-scope", "custom-secret-key")

    assert secret == '{"some": "secret"}'
    mock_dbutils.secrets.get.assert_called_once_with(
        scope="custom-tenant-scope",
        key="custom-secret-key",
    )


# ── 45. Universal Import Without Databricks ───────────────────────────


def test_45_universal_import_without_databricks():
    """45. Core licensing package can be imported and instantiated without Databricks."""
    from backend.app.licensing import (
        LicenseManager,
        LicenseConfig,
        InMemorySecretProvider,
        InMemoryUsageDataSource,
    )

    prov = InMemorySecretProvider()
    vol = InMemoryUsageDataSource(usage=0)
    tok = InMemoryUsageDataSource(usage=0)

    # Core LicenseManager instantiation with generic providers works 100% without Databricks
    mgr = LicenseManager(
        secret_provider=prov,
        volume_usage_source=vol,
        token_usage_source=tok,
    )
    assert mgr.is_licensed is False


# ── 46. Explicit SecretProvider Injection Required (Correction 1) ─────


def test_46_explicit_secret_provider_injection_required():
    """46. LicenseManager requires an explicit SecretProvider and does NOT fallback to Databricks."""
    from pathlib import Path

    # 1. LicenseManager() without secret_provider leaves _provider as None
    mgr = LicenseManager()
    assert mgr._provider is None

    # 2. validate_or_raise() fails deterministically with LicenseConfigurationError
    with pytest.raises(LicenseConfigurationError, match="An explicit SecretProvider is required"):
        mgr.validate_or_raise()

    # 3. Static verification: manager.py has NO Databricks import or fallback instantiation
    manager_path = Path(__file__).resolve().parent.parent / "app" / "licensing" / "manager.py"
    manager_src = manager_path.read_text(encoding="utf-8")
    assert "DatabricksSecretProvider" not in manager_src, "manager.py must not import or instantiate DatabricksSecretProvider"


# ── 47. Explicit Databricks Adapter Injection (Correction 1) ──────────


def test_47_explicit_databricks_adapter_injection(test_keypair):
    """47. LicenseManager works when DatabricksSecretProvider is explicitly injected."""
    from backend.app.licensing.adapters.databricks import DatabricksSecretProvider

    artifact_dict, artifact_json = make_signed_artifact(test_keypair["signing_key"])

    mock_dbutils = MagicMock()
    mock_dbutils.secrets.get.return_value = artifact_json

    prov = DatabricksSecretProvider(dbutils=mock_dbutils)
    cfg = LicenseConfig(public_key_b64=test_keypair["public_b64"])
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    mgr.validate_or_raise()
    assert mgr.is_licensed is True
    mock_dbutils.secrets.get.assert_called_once()


# ── 48. TEST 1 — Signed Artifact Disables Volume ──────────────────────


def test_48_correction_2_test_1_artifact_disables_volume(test_keypair):
    """TEST 1: Local config volume_enabled=1, signed artifact volume.enabled=false.

    VolumeCriterion is NOT executed; application does NOT fail merely because local config says volume_enabled=1.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    mock_vol_source = MagicMock(spec=UsageDataSource)
    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,  # Local config has volume_enabled=1
        volume_limit=10,
        volume_usage_source=mock_vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    # VolumeCriterion was not executed; volume usage source was NOT called
    mock_vol_source.get_current_usage.assert_not_called()
    assert mgr.volume_state.enabled is False


# ── 49. TEST 2 — Signed Artifact Enables Volume ───────────────────────


def test_49_correction_2_test_2_artifact_enables_volume(test_keypair):
    """TEST 2: Local config volume_enabled=0, signed artifact volume.enabled=true, limit=100.

    VolumeCriterion IS executed. Current usage=100 triggers failure (LicenseLimitExceededError).
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=100)
    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=0,  # Local config says volume_enabled=0
        volume_limit=0,
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.limit == 100
    assert exc_info.value.current == 100


# ── 50. TEST 3 — Signed Volume Limit is Authoritative ─────────────────


def test_50_correction_2_test_3_signed_volume_limit_authoritative(test_keypair):
    """TEST 3: Local config volume_limit=999999, signed artifact volume.limit=100, current=100.

    Must fail against signed 100; local 999999 must never override signed limit.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=100)
    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,
        volume_limit=999999,  # Local attempt to raise limit
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.limit == 100
    assert exc_info.value.current == 100


# ── 51. TEST 4 — Signed Token Limit is Authoritative ──────────────────


def test_51_correction_2_test_4_signed_token_limit_authoritative(test_keypair):
    """TEST 4: Local config token_usage_limit=999999, signed artifact token_usage.limit=100, current=100.

    Must fail against signed 100; local 999999 must never override signed limit.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 100},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = InMemoryUsageDataSource(usage=100)
    cfg = LicenseConfig(
        date_enabled=1,
        token_usage_enabled=1,
        token_usage_limit=999999,  # Local attempt to raise limit
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.limit == 100
    assert exc_info.value.current == 100


# ── 52. TEST 5 — Artifact Disables Token Usage ────────────────────────


def test_52_correction_2_test_5_artifact_disables_token_usage(test_keypair):
    """TEST 5: Local config says token enabled, signed artifact says token disabled.

    Token source is NOT called.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    mock_tok_source = MagicMock(spec=UsageDataSource)
    cfg = LicenseConfig(
        date_enabled=1,
        token_usage_enabled=1,  # Local says enabled
        token_usage_limit=50,
        token_usage_source=mock_tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    mock_tok_source.get_current_usage.assert_not_called()
    assert mgr.token_state.enabled is False


# ── 53. TEST 6 — Artifact Disables Date ───────────────────────────────


def test_53_correction_2_test_6_artifact_disables_date(test_keypair):
    """TEST 6: Local config says date enabled, signed artifact says date disabled.

    Expiry is NOT enforced by DateCriterion even if expires_at is in the past.
    """
    past_date = "2020-01-01T00:00:00Z"
    policy = {
        "date": {"enabled": False},  # Artifact disables date criterion
        "volume": {"enabled": True, "limit": 100},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2019-01-01T00:00:00Z",
        expires_at=past_date,
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=10)
    cfg = LicenseConfig(
        date_enabled=1,  # Local config says date_enabled=1
        volume_enabled=1,
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.date_state.enabled is False


# ── 54. TEST 7 — Artifact Enables Date ────────────────────────────────


def test_54_correction_2_test_7_artifact_enables_date_fails_if_expired(test_keypair):
    """TEST 7: Local config says date disabled, signed artifact says date enabled and is expired.

    Startup fails with LicenseExpiredError.
    """
    past_date = "2020-01-01T00:00:00Z"
    policy = {
        "date": {"enabled": True},  # Artifact enables date criterion
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2019-01-01T00:00:00Z",
        expires_at=past_date,
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=10)
    cfg = LicenseConfig(
        date_enabled=0,  # Local config claims date is disabled
        volume_enabled=1,
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseExpiredError):
        mgr.validate_or_raise()


# ── 55. TEST 8 — No Fallback to Local Policy ──────────────────────────


def test_55_correction_2_test_8_no_fallback_to_local_policy(test_keypair):
    """TEST 8: Every local enforcement flag and limit changed to contradictory values.

    Runtime behavior remains exactly determined by the signed artifact policy.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=50)
    mock_tok_source = MagicMock(spec=UsageDataSource)

    # Local config has completely contradictory values:
    # - Claims date_enabled=0
    # - Claims volume_enabled=0
    # - Claims volume_limit=10 (which usage 50 would violate if local limit was used!)
    # - Claims token_usage_enabled=0
    # - Claims token_usage_limit=10
    cfg = LicenseConfig(
        date_enabled=0,
        volume_enabled=0,
        volume_limit=10,
        token_usage_enabled=0,
        token_usage_limit=10,
        volume_usage_source=vol_source,
        token_usage_source=mock_tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    # Signed volume limit of 500 governed enforcement (usage 50 <= 500 passed)
    assert mgr.volume_state.limit == 500
    assert mgr.volume_state.current == 50
    # Signed token usage was disabled, so mock token source was never called
    mock_tok_source.get_current_usage.assert_not_called()
    assert mgr.token_state.enabled is False
    # Signed date was enabled and valid
    assert mgr.date_state.enabled is True


# ── 56. Test A — Local 0/0/0 does not block valid signed policy ───────


def test_56_test_a_local_000_does_not_block_valid_signed_policy(test_keypair):
    """Test A: Local date_enabled=0, volume_enabled=0, token_usage_enabled=0.

    Signed artifact has date.enabled=True, volume.enabled=False, token_usage.enabled=False.
    Expected: LicenseManager startup validation succeeds; Date criterion enforced; local 0/0/0 does not block runtime.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    cfg = LicenseConfig(
        date_enabled=0,
        volume_enabled=0,
        token_usage_enabled=0,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.date_state.enabled is True
    assert mgr.date_state.passed is True
    assert mgr.volume_state.enabled is False
    assert mgr.token_state.enabled is False


# ── 57. Test B — Local enabled flags do not override artifact disabled flags 


def test_57_test_b_local_enabled_flags_do_not_override_artifact_disabled_flags(test_keypair):
    """Test B: Local date_enabled=1, volume_enabled=1, token_usage_enabled=1.

    Artifact has 0/0/0 (date.enabled=False, volume.enabled=False, token_usage.enabled=False).
    Artifact must be rejected by policy validation because 0/0/0 in signed policy is invalid.
    Local enabled flags do NOT rescue the invalid artifact.
    """
    future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_payload = {
        "license_id": "CLIENT-ALTERYX-001",
        "product": "alteryx-etl",
        "environment": "production",
        "issued_at": "2026-10-06T00:00:00Z",
        "expires_at": future,
        "features": {
            "workflow_analysis": True,
            "portfolio_rationalisation": True,
            "python_translation": True,
            "export_reports": True,
        },
        "policy": {
            "date": {"enabled": False},
            "volume": {"enabled": False, "limit": 0},
            "token_usage": {"enabled": False, "limit": 0},
        },
    }
    canonical_bytes = canonical_payload(raw_payload)
    sig = test_keypair["signing_key"].sign(canonical_bytes).signature
    sig_b64 = base64.b64encode(sig).decode("ascii")
    raw_payload["signature"] = sig_b64
    artifact_json = json.dumps(raw_payload)

    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=0)
    tok_source = InMemoryUsageDataSource(usage=0)
    cfg = LicenseConfig(
        date_enabled=1,
        volume_enabled=1,
        token_usage_enabled=1,
        volume_limit=100,
        token_usage_limit=1000,
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseInvalidError) as exc_info:
        mgr.validate_or_raise()
    err_msg = str(exc_info.value)
    assert "0/0/0 combination is rejected" in err_msg or "At least one criterion must be enabled" in err_msg


# ── 58. Test C — Local volume limit does not override artifact volume limit ──


def test_58_test_c_local_volume_limit_does_not_override_artifact_limit(test_keypair):
    """Test C: Local volume_limit=10, artifact volume.limit=500, volume.enabled=True.

    Current usage=100.
    Must remain valid because 100 < 500. Local value 10 does not cause failure.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = InMemoryUsageDataSource(usage=100)
    cfg = LicenseConfig(
        volume_limit=10,  # Local attempt to restrict limit
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.volume_state.limit == 500
    assert mgr.volume_state.current == 100


# ── 59. Test D — Local token limit does not override artifact token limit ───


def test_59_test_d_local_token_limit_does_not_override_artifact_limit(test_keypair):
    """Test D: Local token_usage_limit=100, artifact token_usage.limit=500000, token_usage.enabled=True.

    Current usage=1000.
    Must remain valid because 1000 < 500000. Local value 100 does not cause failure.
    """
    policy = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = InMemoryUsageDataSource(usage=1000)
    cfg = LicenseConfig(
        token_usage_limit=100,  # Local attempt to restrict limit
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.token_state.limit == 500000
    assert mgr.token_state.current == 1000


# ── 60. Test E — Artifact policy still controls enforcement ───────────


def test_60_test_e_artifact_policy_still_controls_enforcement(test_keypair):
    """Test E: Verify that when current usage reaches signed limit, runtime fails closed.

    1. Volume: limit=500, current=500 -> LicenseLimitExceededError
    2. Token: limit=500000, current=500000 -> LicenseLimitExceededError
    """
    # 1. Volume fail-closed at limit
    policy_vol = {
        "date": {"enabled": True},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_vol_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy_vol,
    )
    prov_vol = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_vol_json})
    vol_source = InMemoryUsageDataSource(usage=500)
    cfg_vol = LicenseConfig(
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr_vol = LicenseManager(config=cfg_vol, secret_provider=prov_vol)
    with pytest.raises(LicenseLimitExceededError) as exc_info_vol:
        mgr_vol.validate_or_raise()
    assert exc_info_vol.value.limit == 500
    assert exc_info_vol.value.current == 500

    # 2. Token usage fail-closed at limit
    policy_tok = {
        "date": {"enabled": True},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_tok_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy_tok,
    )
    prov_tok = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_tok_json})
    tok_source = InMemoryUsageDataSource(usage=500000)
    cfg_tok = LicenseConfig(
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr_tok = LicenseManager(config=cfg_tok, secret_provider=prov_tok)
    with pytest.raises(LicenseLimitExceededError) as exc_info_tok:
        mgr_tok.validate_or_raise()
    assert exc_info_tok.value.limit == 500000
    assert exc_info_tok.value.current == 500000



