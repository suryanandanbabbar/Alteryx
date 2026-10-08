"""Secret provider abstraction for license artifact retrieval."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from .errors import LicenseSecretError

logger = logging.getLogger("awa.licensing.secret_provider")


@runtime_checkable
class SecretProvider(Protocol):
    """Protocol for retrieving secrets from secret storage."""

    def get_secret(self, scope: str, key: str) -> str:
        """Retrieve secret string from the given scope and key.

        Args:
            scope: Secret scope name.
            key: Secret name within the scope.

        Returns:
            The raw secret string content.

        Raises:
            LicenseSecretError: If retrieval fails, the secret is empty, or the scope is unavailable.
        """
        ...


class InMemorySecretProvider:
    """In-memory SecretProvider for testing and local development injection."""

    def __init__(self, secrets: dict[tuple[str, str], str] | None = None) -> None:
        self._secrets: dict[tuple[str, str], str] = dict(secrets or {})

    def set_secret(self, scope: str, key: str, value: str) -> None:
        """Set a secret in the mock store."""
        self._secrets[(scope, key)] = value

    def get_secret(self, scope: str, key: str) -> str:
        """Retrieve secret from the in-memory map."""
        if (scope, key) not in self._secrets:
            raise LicenseSecretError(
                f"Secret '{key}' not found in scope '{scope}'."
            )
        val = self._secrets[(scope, key)]
        if val is None or not str(val).strip():
            raise LicenseSecretError(
                f"Secret '{key}' in scope '{scope}' is empty."
            )
        return str(val)


# Lazy alias for backward compatibility without importing Databricks at module level
def __getattr__(name: str):
    if name == "DatabricksSecretProvider":
        from .adapters.databricks import DatabricksSecretProvider
        return DatabricksSecretProvider
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
