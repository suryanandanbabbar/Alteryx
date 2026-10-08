"""Databricks Secret Scope adapter for license secret retrieval."""

from __future__ import annotations

import logging
from typing import Any

from ..errors import LicenseSecretError

logger = logging.getLogger("awa.licensing.adapters.databricks")


class DatabricksSecretProvider:
    """Databricks secret provider adapter implementing the SecretProvider protocol.

    Retrieves secrets dynamically from Databricks Secret Scopes using dbutils.
    Does not hardcode any scope names or keys.
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
        """Retrieve secret string from Databricks Secret Scope dynamically.

        Args:
            scope: Secret scope name configured by the application.
            key: Secret name configured by the application.

        Returns:
            The raw secret string content.

        Raises:
            LicenseSecretError: If retrieval fails, secret is empty, or dbutils is unavailable.
        """
        dbutils = self._resolve_dbutils()

        try:
            secret_value = dbutils.secrets.get(
                scope=scope,
                key=key,
            )
        except Exception as exc:
            raise LicenseSecretError(
                f"Failed to retrieve secret '{key}' from scope '{scope}': {exc}"
            ) from exc

        if secret_value is None or not str(secret_value).strip():
            raise LicenseSecretError(
                f"Secret '{key}' in scope '{scope}' is empty."
            )

        return str(secret_value)
