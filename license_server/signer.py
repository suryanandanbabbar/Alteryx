"""Ed25519 signing engine using the cryptography library.

Signs canonical JSON payloads using the authoritative Ed25519 private key
loaded securely from Azure Key Vault.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from .errors import SigningError

logger = logging.getLogger("license_server.signer")


class LicenseSigner:
    """Signs canonical license responses using an Ed25519 private key."""

    def __init__(
        self,
        private_key: Ed25519PrivateKey | None = None,
        key_vault_client: Any = None,
        secret_name: str = "alteryx-license-private-key",
    ) -> None:
        """Initialize with either an active Ed25519PrivateKey or a Key Vault client."""
        self._private_key = private_key
        self._key_vault_client = key_vault_client
        self._secret_name = secret_name

    def _ensure_private_key(self) -> Ed25519PrivateKey:
        """Lazily load private key from Key Vault if not already present."""
        if self._private_key is not None:
            return self._private_key

        if self._key_vault_client is None:
            raise SigningError("Neither Ed25519PrivateKey nor Key Vault client was provided.")

        try:
            # Check get_secret or get_private_key_pem
            if hasattr(self._key_vault_client, "get_secret"):
                raw_val = self._key_vault_client.get_secret(self._secret_name)
            elif hasattr(self._key_vault_client, "get_private_key_pem"):
                raw_val = self._key_vault_client.get_private_key_pem(self._secret_name)
            else:
                raise SigningError("Key Vault client does not implement secret retrieval.")

            self._private_key = self._parse_key(raw_val)
            return self._private_key
        except SigningError:
            raise
        except Exception as exc:
            logger.error("Failed to load signing key: %s", type(exc).__name__)
            raise SigningError("Unable to load signing key from secure key storage.") from exc

    @staticmethod
    def _parse_key(raw_val: str | bytes) -> Ed25519PrivateKey:
        """Parse private key from PEM bytes/str, or base64 32-byte raw key without exposing key material."""
        raw_bytes = raw_val.encode("utf-8") if isinstance(raw_val, str) else raw_val

        # 1. Try PEM format
        if b"-----BEGIN" in raw_bytes:
            try:
                key = load_pem_private_key(raw_bytes, password=None)
                if isinstance(key, Ed25519PrivateKey):
                    return key
                raise SigningError("Parsed signing key is not a valid Ed25519 key.")
            except SigningError:
                raise
            except Exception as exc:
                raise SigningError("Failed to parse private key from secure storage.") from exc

        # 2. Try Base64-encoded raw 32 bytes
        try:
            decoded = base64.b64decode(raw_bytes)
            if len(decoded) == 32:
                return Ed25519PrivateKey.from_private_bytes(decoded)
        except Exception:
            pass

        # 3. Try raw 32 bytes directly
        if len(raw_bytes) == 32:
            try:
                return Ed25519PrivateKey.from_private_bytes(raw_bytes)
            except Exception as exc:
                raise SigningError("Failed to parse raw 32-byte private key from secure storage.") from exc

        raise SigningError("Unrecognized private key format in secure storage.")

    @classmethod
    def from_pem(cls, pem_bytes: bytes | str) -> LicenseSigner:
        """Create a signer by loading PEM-encoded private key bytes."""
        key = cls._parse_key(pem_bytes)
        return cls(private_key=key)

    def sign(self, canonical_bytes: bytes) -> str:
        """Compute Ed25519 signature over canonical payload bytes.

        Args:
            canonical_bytes: UTF-8 encoded canonical JSON payload.

        Returns:
            Base64-encoded signature string (64 raw bytes -> 88 chars).

        Raises:
            SigningError: If signing fails.
        """
        try:
            key = self._ensure_private_key()
            signature_raw = key.sign(canonical_bytes)
            return base64.b64encode(signature_raw).decode("ascii")
        except SigningError:
            raise
        except Exception as exc:
            logger.error("Signing failed: %s", type(exc).__name__)
            raise SigningError("Cryptographic signing operation failed.") from exc
