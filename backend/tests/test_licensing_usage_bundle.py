"""Automated tests for Volume and Token Usage licensing criteria with SQLite usage test bundle.

Validates that:
1. Volume and Token Usage criteria consume current cumulative usage via UsageDataSource.
2. Limits are enforced exclusively from the VERIFIED SIGNED LICENSE ARTIFACT POLICY.
3. Fail-closed behavior on boundary conditions and source query errors.
4. Local developer configurations cannot override signed artifact policies.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from backend.app.licensing.config import LicenseConfig
from backend.app.licensing.errors import LicenseInvalidError, LicenseLimitExceededError
from backend.app.licensing.licensing_usage_test_bundle.sqlite_usage_source_test import (
    SQLiteUsageDataSource,
)
from backend.app.licensing.manager import LicenseManager
from backend.app.licensing.secret_provider import InMemorySecretProvider
from backend.tests.test_licensing import make_signed_artifact, test_keypair

BUNDLE_DIR = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "licensing"
    / "licensing_usage_test_bundle"
)
BUNDLE_DB_PATH = BUNDLE_DIR / "licensing_usage_test.db"


def reset_db(db_path: Path | str) -> None:
    """Reset the SQLite test database to canonical seeded values."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE volume_usage SET current_usage = 100, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
        )
        conn.execute(
            "UPDATE token_usage SET current_usage = 10000, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
        )
        conn.commit()


def set_usage(db_path: Path | str, table: str, value: int | str) -> None:
    """Set current usage in the specified singleton table."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            f"UPDATE {table} SET current_usage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (value,),
        )
        conn.commit()


def get_usage(db_path: Path | str, table: str) -> int:
    """Get current usage from the specified singleton table."""
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(f"SELECT current_usage FROM {table} WHERE id = 1").fetchone()
        return row[0]


@pytest.fixture(autouse=True)
def ensure_bundle_db_clean():
    """Ensure the shared test database always ends in the clean seeded state."""
    try:
        yield
    finally:
        if BUNDLE_DB_PATH.exists():
            reset_db(BUNDLE_DB_PATH)


@pytest.fixture
def isolated_db(tmp_path):
    """Provide an isolated copy of licensing_usage_test.db per test."""
    db_copy = tmp_path / "licensing_usage_test.db"
    shutil.copy2(BUNDLE_DB_PATH, db_copy)
    return db_copy


# ── Section 5: Volume Criterion Tests ─────────────────────────────────


def test_5_1_volume_below_limit(isolated_db, test_keypair):
    """Test 5.1: Volume below limit: 100 < 500 -> PASS."""
    set_usage(isolated_db, "volume_usage", 100)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        volume_usage_source=vol_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.volume_state.passed is True
    assert mgr.volume_state.current == 100
    assert mgr.volume_state.limit == 500


def test_5_2_volume_exactly_at_limit(isolated_db, test_keypair):
    """Test 5.2: Volume exactly at limit: 500 >= 500 -> FAIL CLOSED."""
    set_usage(isolated_db, "volume_usage", 500)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        volume_usage_source=vol_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.criterion == "volume"
    assert exc_info.value.current == 500
    assert exc_info.value.limit == 500


def test_5_3_volume_above_limit(isolated_db, test_keypair):
    """Test 5.3: Volume above limit: 501 >= 500 -> FAIL CLOSED."""
    set_usage(isolated_db, "volume_usage", 501)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        volume_usage_source=vol_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.criterion == "volume"
    assert exc_info.value.current == 501
    assert exc_info.value.limit == 500


def test_5_4_volume_reset(isolated_db, test_keypair):
    """Test 5.4: Volume reset to 100 restores validity."""
    set_usage(isolated_db, "volume_usage", 500)
    # Reset
    set_usage(isolated_db, "volume_usage", 100)
    assert get_usage(isolated_db, "volume_usage") == 100

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        volume_usage_source=vol_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()
    assert mgr.is_licensed is True


# ── Section 6: Token Usage Criterion Tests ────────────────────────────


def test_6_1_token_usage_below_limit(isolated_db, test_keypair):
    """Test 6.1: Token usage below limit: 10000 < 500000 -> PASS."""
    set_usage(isolated_db, "token_usage", 10000)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        token_usage_source=tok_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.token_state.passed is True
    assert mgr.token_state.current == 10000
    assert mgr.token_state.limit == 500000


def test_6_2_token_usage_exactly_at_limit(isolated_db, test_keypair):
    """Test 6.2: Token usage exactly at limit: 500000 >= 500000 -> FAIL CLOSED."""
    set_usage(isolated_db, "token_usage", 500000)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        token_usage_source=tok_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.criterion == "token_usage"
    assert exc_info.value.current == 500000
    assert exc_info.value.limit == 500000


def test_6_3_token_usage_above_limit(isolated_db, test_keypair):
    """Test 6.3: Token usage above limit: 500001 >= 500000 -> FAIL CLOSED."""
    set_usage(isolated_db, "token_usage", 500001)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        token_usage_source=tok_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseLimitExceededError) as exc_info:
        mgr.validate_or_raise()

    assert exc_info.value.criterion == "token_usage"
    assert exc_info.value.current == 500001
    assert exc_info.value.limit == 500000


def test_6_4_token_usage_reset(isolated_db, test_keypair):
    """Test 6.4: Token usage reset to 10000 restores validity."""
    set_usage(isolated_db, "token_usage", 500000)
    # Reset
    set_usage(isolated_db, "token_usage", 10000)
    assert get_usage(isolated_db, "token_usage") == 10000

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        public_key_b64=test_keypair["public_b64"],
        token_usage_source=tok_source,
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()
    assert mgr.is_licensed is True


# ── Section 7: Local Configuration Cannot Override Artifact ──────────


def test_7_local_limits_cannot_override_signed_limits(isolated_db, test_keypair):
    """Test 7: Local limits (volume_limit=10, token_usage_limit=100) cannot override signed limits (500, 500000)."""
    set_usage(isolated_db, "volume_usage", 100)
    set_usage(isolated_db, "token_usage", 10000)

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")

    cfg = LicenseConfig(
        volume_limit=10,  # Lower than current usage 100
        token_usage_limit=100,  # Lower than current usage 10000
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    # Signed artifact limits of 500 and 500000 are authoritative
    assert mgr.volume_state.limit == 500
    assert mgr.volume_state.current == 100
    assert mgr.token_state.limit == 500000
    assert mgr.token_state.current == 10000


# ── Section 8: Local Enabled Flags Cannot Override Artifact Policy ────


def test_8_local_enabled_flags_cannot_override_artifact_policy(isolated_db, test_keypair):
    """Test 8: Local date_enabled=1 cannot force date enforcement if signed artifact has date.enabled=False."""
    past_date = "2020-01-01T00:00:00Z"
    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        issued_at="2019-01-01T00:00:00Z",
        expires_at=past_date,  # Past date
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")

    cfg = LicenseConfig(
        date_enabled=1,  # Local claims date enabled
        volume_enabled=1,
        token_usage_enabled=1,
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    assert mgr.is_licensed is True
    assert mgr.date_state.enabled is False


# ── Section 9: Usage Source Failure Fail-Closed ───────────────────────


def test_9_1_usage_source_unavailable_db_fails_closed(test_keypair):
    """Test 9.1: Unavailable database file fails closed with LicenseInvalidError."""
    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(Path("/nonexistent/path/db.sqlite"), "volume_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseInvalidError) as exc_info:
        mgr.validate_or_raise()
    assert "Failed to retrieve current volume usage from source" in str(exc_info.value)


def test_9_2_missing_singleton_row_fails_closed(isolated_db, test_keypair):
    """Test 9.2: Missing singleton row (id=1) fails closed with LicenseInvalidError."""
    with sqlite3.connect(str(isolated_db)) as conn:
        conn.execute("DELETE FROM volume_usage WHERE id = 1")
        conn.commit()

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseInvalidError):
        mgr.validate_or_raise()


def test_9_3_invalid_negative_usage_fails_closed(isolated_db, test_keypair):
    """Test 9.3: Negative usage value in database fails closed with LicenseInvalidError."""
    with sqlite3.connect(str(isolated_db)) as conn:
        conn.execute("CREATE TABLE temp_vol (id INT, current_usage INT, updated_at TEXT)")
        conn.execute("INSERT INTO temp_vol VALUES (1, -5, CURRENT_TIMESTAMP)")
        conn.execute("DROP TABLE volume_usage")
        conn.execute("ALTER TABLE temp_vol RENAME TO volume_usage")
        conn.commit()

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": False, "limit": 0},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseInvalidError):
        mgr.validate_or_raise()


def test_9_4_malformed_string_usage_fails_closed(isolated_db, test_keypair):
    """Test 9.4: Malformed string usage in database fails closed with LicenseInvalidError."""
    with sqlite3.connect(str(isolated_db)) as conn:
        conn.execute("UPDATE token_usage SET current_usage = 'corrupt' WHERE id = 1")
        conn.commit()

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": False, "limit": 0},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)

    with pytest.raises(LicenseInvalidError):
        mgr.validate_or_raise()


# ── Section 10: Cumulative Usage Semantics (Consumer Only) ───────────


def test_10_cumulative_usage_semantics_consumer_only(isolated_db, test_keypair):
    """Test 10: LicenseManager only consumes usage; does NOT modify or write to database."""
    with sqlite3.connect(str(isolated_db)) as conn:
        vol_before = conn.execute("SELECT current_usage, updated_at FROM volume_usage WHERE id = 1").fetchone()
        tok_before = conn.execute("SELECT current_usage, updated_at FROM token_usage WHERE id = 1").fetchone()

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()

    with sqlite3.connect(str(isolated_db)) as conn:
        vol_after = conn.execute("SELECT current_usage, updated_at FROM volume_usage WHERE id = 1").fetchone()
        tok_after = conn.execute("SELECT current_usage, updated_at FROM token_usage WHERE id = 1").fetchone()

    assert vol_before == vol_after, "Volume record must not be modified during licensing validation"
    assert tok_before == tok_after, "Token usage record must not be modified during licensing validation"


# ── Section 11: Both Criteria Together ────────────────────────────────


def test_11_both_criteria_together(isolated_db, test_keypair):
    """Test 11: Both Volume and Token Usage criteria enabled simultaneously."""
    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(isolated_db, "volume_usage")
    tok_source = SQLiteUsageDataSource(isolated_db, "token_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )

    # 1. Below both limits: vol=100, tok=10000 -> PASS
    set_usage(isolated_db, "volume_usage", 100)
    set_usage(isolated_db, "token_usage", 10000)
    mgr1 = LicenseManager(config=cfg, secret_provider=prov)
    mgr1.validate_or_raise()
    assert mgr1.is_licensed is True

    # 2. Volume at limit: vol=500, tok=10000 -> FAIL CLOSED on volume
    set_usage(isolated_db, "volume_usage", 500)
    mgr2 = LicenseManager(config=cfg, secret_provider=prov)
    with pytest.raises(LicenseLimitExceededError) as exc2:
        mgr2.validate_or_raise()
    assert exc2.value.criterion == "volume"

    # 3. Token at limit: vol=100, tok=500000 -> FAIL CLOSED on token_usage
    set_usage(isolated_db, "volume_usage", 100)
    set_usage(isolated_db, "token_usage", 500000)
    mgr3 = LicenseManager(config=cfg, secret_provider=prov)
    with pytest.raises(LicenseLimitExceededError) as exc3:
        mgr3.validate_or_raise()
    assert exc3.value.criterion == "token_usage"


# ── Direct End-to-End Test Against Live Test Bundle DB ────────────────


def test_12_direct_live_bundle_db_validation(test_keypair):
    """Test 12: Direct verification using the live licensing_usage_test.db artifact."""
    assert BUNDLE_DB_PATH.exists(), f"Test database bundle missing at {BUNDLE_DB_PATH}"

    # Verify initial seeded values
    assert get_usage(BUNDLE_DB_PATH, "volume_usage") == 100
    assert get_usage(BUNDLE_DB_PATH, "token_usage") == 10000

    policy = {
        "date": {"enabled": False},
        "volume": {"enabled": True, "limit": 500},
        "token_usage": {"enabled": True, "limit": 500000},
    }
    _, artifact_json = make_signed_artifact(
        test_keypair["signing_key"],
        policy=policy,
    )
    prov = InMemorySecretProvider({("alteryx-licenseArtifacts", "alteryx-license"): artifact_json})

    vol_source = SQLiteUsageDataSource(BUNDLE_DB_PATH, "volume_usage")
    tok_source = SQLiteUsageDataSource(BUNDLE_DB_PATH, "token_usage")
    cfg = LicenseConfig(
        volume_usage_source=vol_source,
        token_usage_source=tok_source,
        public_key_b64=test_keypair["public_b64"],
    )

    # 1. Live pass
    mgr = LicenseManager(config=cfg, secret_provider=prov)
    mgr.validate_or_raise()
    assert mgr.is_licensed is True

    # 2. Live volume boundary
    try:
        set_usage(BUNDLE_DB_PATH, "volume_usage", 500)
        mgr_fail = LicenseManager(config=cfg, secret_provider=prov)
        with pytest.raises(LicenseLimitExceededError):
            mgr_fail.validate_or_raise()
    finally:
        set_usage(BUNDLE_DB_PATH, "volume_usage", 100)

    # 3. Live token boundary
    try:
        set_usage(BUNDLE_DB_PATH, "token_usage", 500000)
        mgr_fail_tok = LicenseManager(config=cfg, secret_provider=prov)
        with pytest.raises(LicenseLimitExceededError):
            mgr_fail_tok.validate_or_raise()
    finally:
        set_usage(BUNDLE_DB_PATH, "token_usage", 10000)

    # Confirm final state is restored
    assert get_usage(BUNDLE_DB_PATH, "volume_usage") == 100
    assert get_usage(BUNDLE_DB_PATH, "token_usage") == 10000
