"""Tests for canonical JSON payload generation.

Validates that server-side canonicalization strictly matches client-side
canonicalization byte-for-byte, keys are sorted deterministically,
and the signature field is excluded.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from license_server.canonical import canonical_payload as server_canonical
from backend.app.licensing.verifier import canonical_payload as client_canonical


def test_canonical_byte_for_byte_identity_with_client():
    """Server canonical_payload must produce identical UTF-8 bytes to client canonical_payload."""
    sample_data = {
        "license_id": "LIC-PROD-2026-001",
        "product": "alteryx-etl",
        "environment": "production",
        "client_instance_id": "inst-abcd-1234",
        "request_id": "req-xyz-789",
        "status": "active",
        "lease_expires_at": "2026-10-06T12:00:00+00:00",
        "server_time": "2026-10-05T12:00:00+00:00",
        "features": {"pdf_export": True, "sttm": True},
        "message": "License is active and in good standing.",
        "signature": "SHOULD_BE_STRIPPED_OFF",
    }

    server_bytes = server_canonical(sample_data)
    client_bytes = client_canonical(sample_data)

    assert server_bytes == client_bytes
    assert b"SHOULD_BE_STRIPPED_OFF" not in server_bytes
    assert b"signature" not in server_bytes


def test_canonical_excludes_signature_field():
    """Ensure the signature field is never included in the canonical bytes."""
    payload_with_sig = {
        "status": "active",
        "license_id": "LIC-001",
        "signature": "MOCK_SIGNATURE_BASE64",
    }
    payload_without_sig = {
        "status": "active",
        "license_id": "LIC-001",
    }

    assert server_canonical(payload_with_sig) == server_canonical(payload_without_sig)


def test_canonical_sorts_keys_deterministically():
    """Payload key insertion order must not change canonical byte output."""
    d1 = {"z": 1, "a": 2, "m": 3}
    d2 = {"a": 2, "m": 3, "z": 1}
    d3 = {"m": 3, "z": 1, "a": 2}

    bytes1 = server_canonical(d1)
    bytes2 = server_canonical(d2)
    bytes3 = server_canonical(d3)

    assert bytes1 == bytes2 == bytes3
    assert bytes1 == b'{"a":2,"m":3,"z":1}'


def test_canonical_compact_separators():
    """Ensure no whitespace exists around separators ',' and ':'."""
    data = {"key1": "val1", "key2": "val2", "nested": {"k": "v"}}
    result = server_canonical(data).decode("utf-8")

    assert ", " not in result
    assert ": " not in result
    assert result == '{"key1":"val1","key2":"val2","nested":{"k":"v"}}'
