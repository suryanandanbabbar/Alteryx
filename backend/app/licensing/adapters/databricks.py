"""Databricks App Secret adapter for license secret retrieval."""

from __future__ import annotations

import logging
import os

from ..errors import LicenseSecretError

logger = logging.getLogger("awa.licensing.adapters.databricks")

_ENV_VAR_NAME = "ALTERYX_LICENSE_ARTIFACT"


class DatabricksSecretProvider:
    """Databricks App secret provider adapter implementing the SecretProvider protocol.

    Retrieves secrets injected into the Databricks App runtime via the
    configured Secret App Resource environment variable ('ALTERYX_LICENSE_ARTIFACT').
    Does not require cluster or notebook dbutils in the Databricks Apps runtime.
    """

    def __init__(self, env_var: str = _ENV_VAR_NAME) -> None:
        self._env_var = env_var

    def get_secret(self, scope: str, key: str) -> str:
        """Retrieve secret string from the Databricks App environment.

        Args:
            scope: Secret scope name configured by the application.
            key: Secret name configured by the application.

        Returns:
            The raw secret string content.

        Raises:
            LicenseSecretError: If the environment variable is missing, empty, or whitespace-only.
        """
        secret_value = os.getenv(self._env_var)

        if secret_value is None or not str(secret_value).strip():
            logger.error(
                "Databricks App secret environment variable '%s' is missing or empty.",
                self._env_var,
            )
            raise LicenseSecretError(
                f"Databricks App secret environment variable '{self._env_var}' is missing or empty."
            )

        return str(secret_value)
