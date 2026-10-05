"""Ed25519 signature verification for Azure License API responses.

The canonical payload format (compact sorted JSON, signature field excluded)
must be identical on both the Azure signing side and the client verification
side.  Any change to the canonical format is a breaking change.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from .errors import LicenseSignatureError

logger = logging.getLogger("awa.licensing.verifier")


def canonical_payload(data: dict[str, Any]) -> bytes:
    """Create canonical byte representation for Ed25519 signature verification.

    Algorithm:
      1. Remove the ``signature`` key from the dict.
      2. Serialise remaining keys as compact JSON with sorted keys.
      3. Encode as UTF-8 bytes.

    The ``default=str`` fallback handles datetime strings or other types
    that may appear in the raw JSON response dict.

    Both the Azure signing function and this client function MUST produce
    identical output for the same logical payload.
    """
    filtered = {k: v for k, v in data.items() if k != "signature"}
    return json.dumps(
        filtered,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def verify_signature(
    payload_dict: dict[str, Any],
    signature_b64: str,
    public_key_b64: str,
) -> bool:
    """Verify Ed25519 signature on the canonical payload.

    Args:
        payload_dict: Raw JSON response dict (``signature`` field is excluded
            from the canonical payload automatically).
        signature_b64: Base64-encoded Ed25519 signature from the response.
        public_key_b64: Base64-encoded Ed25519 public key (32 bytes).

    Returns:
        ``True`` if the signature is valid.

    Raises:
        LicenseSignatureError: If verification fails, keys are malformed,
            or the PyNaCl library is not available.
    """
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except ImportError as exc:
        raise LicenseSignatureError(
            "PyNaCl library is required for license verification but is not installed. "
            "Install with: pip install PyNaCl>=1.5.0"
        ) from exc

    # Decode key and signature
    try:
        public_key_bytes = base64.b64decode(public_key_b64)
    except Exception as exc:
        raise LicenseSignatureError(
            f"Failed to decode public key from base64: {type(exc).__name__}"
        ) from exc

    try:
        signature_bytes = base64.b64decode(signature_b64)
    except Exception as exc:
        raise LicenseSignatureError(
            f"Failed to decode signature from base64: {type(exc).__name__}"
        ) from exc

    if len(public_key_bytes) != 32:
        raise LicenseSignatureError(
            f"Invalid Ed25519 public key length: expected 32 bytes, got {len(public_key_bytes)}."
        )

    # Build canonical message
    message = canonical_payload(payload_dict)

    # Verify
    try:
        verify_key = VerifyKey(public_key_bytes)
        verify_key.verify(message, signature_bytes)
        return True
    except BadSignatureError:
        raise LicenseSignatureError(
            "Ed25519 signature verification failed: "
            "payload has been tampered with or wrong signing key was used."
        )
    except Exception as exc:
        raise LicenseSignatureError(
            f"Signature verification error: {type(exc).__name__}"
        ) from exc
