"""Secret provider abstraction for Databricks Key Vault-backed secret scope."""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from .errors import LicenseSecretError

logger = logging.getLogger("awa.licensing.secret_provider")


@runtime_checkable
class SecretProvider(Protocol):
    """Protocol for retrieving secrets from secret storage."""

    def get_secret(self, scope: str, key: str) -> str:
        """Retrieve secret string from the given scope and key.

        Args:
            scope: Secret scope name (e.g. alteryx-licenseArtifacts).
            key: Secret name within the scope (e.g. alteryx-license).

        Returns:
            The raw secret string content.

        Raises:
            LicenseSecretError: If retrieval fails, the secret is empty, or the scope is unavailable.
        """
        ...


class DatabricksSecretProvider:
    """Production provider retrieving secrets via Databricks dbutils.secrets.

    Isolates the Databricks runtime dependency so the rest of the application
    does not depend on globally imported dbutils.
    """

    def __init__(self, dbutils: Any = None) -> None:
        self._dbutils = dbutils

    def _resolve_dbutils(self) -> Any:
        if self._dbutils is not None:
            return self._dbutils

        # 1. Builtins (standard interactive Databricks notebooks / environments)
        import builtins

        if hasattr(builtins, "dbutils"):
            return getattr(builtins, "dbutils")

        # 2. Global namespace of entry module (__main__)
        import sys

        main_mod = sys.modules.get("__main__")
        if main_mod and hasattr(main_mod, "dbutils"):
            return getattr(main_mod, "dbutils")

        # 3. PySpark DBUtils factory
        try:
            from pyspark.dbutils import DBUtils
            from pyspark.sql import SparkSession

            spark = SparkSession.builder.getOrCreate()
            return DBUtils(spark)
        except Exception:
            pass

        # 4. Databricks Runtime DBUtils module
        try:
            import dbruntime.dbutils

            return dbruntime.dbutils.DBUtils()
        except Exception:
            pass

        raise LicenseSecretError(
            "Databricks dbutils is not available in the current runtime environment."
        )

    def get_secret(self, scope: str, key: str) -> str:
        """Retrieve secret from Databricks secret scope."""
        logger.info(
            "Retrieving license secret from Databricks scope: scope=%s key=%s", scope, key)
        try:
            dbutils = self._resolve_dbutils()
            secret_value = dbutils.secrets.get(scope=scope, key=key)
            if secret_value is None or not str(secret_value).strip():
                raise LicenseSecretError(
                    f"Secret '{key}' in scope '{scope}' is empty."
                )
            return str(secret_value)
        except LicenseSecretError:
            raise
        except Exception as exc:
            logger.error(
                "License secret retrieval failed for scope=%s key=%s (%s)",
                scope,
                key,
                type(exc).__name__,
            )
            raise LicenseSecretError(
                f"Failed to retrieve secret '{key}' from Databricks scope '{scope}'."
            ) from exc


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
