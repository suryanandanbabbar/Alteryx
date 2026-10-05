"""Azure Key Vault integration using Managed Identity.

SECURITY SPECIFICATION:
The private signing key is never distributed to the client, never persisted to
application disk, never returned by the API, never logged, and remains within
the Azure-controlled License API trust boundary.

KEY ROTATION POLICY:
The signing key is cached in process memory for performance and operational stability.
Rotating the Key Vault secret requires an application restart or reload before the new
key is loaded into active memory.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from .errors import KeyVaultError

logger = logging.getLogger("license_server.keyvault")


class KeyVaultClientProtocol(Protocol):
    """Protocol for Key Vault clients allowing test injection."""

    def get_secret(self, secret_name: str) -> str:
        ...

    def get_private_key_pem(self, secret_name: str) -> bytes:
        ...


class AzureKeyVaultClient:
    """Production Azure Key Vault client utilizing DefaultAzureCredential.

    In Azure App Service, DefaultAzureCredential authenticates via the
    System-Assigned Managed Identity. In local development, it falls back
    to Azure CLI credentials.
    """

    def __init__(self, vault_url: str) -> None:
        """Initialize the Key Vault client configuration.

        Args:
            vault_url: Azure Key Vault URL (e.g. https://<vault-name>.vault.azure.net/)
        """
        self._vault_url = vault_url.rstrip("/") if vault_url else ""
        self._cache: dict[str, str] = {}
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize SecretClient."""
        if self._client is not None:
            return self._client

        if not self._vault_url:
            raise KeyVaultError("AZURE_KEY_VAULT_URL is not configured.")

        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=self._vault_url, credential=credential)
            return self._client
        except Exception as exc:
            logger.error("Failed to initialize Azure Key Vault SecretClient: %s", type(exc).__name__)
            raise KeyVaultError("Could not initialize Key Vault credentials.") from exc

    def get_secret(self, secret_name: str) -> str:
        """Retrieve a secret string from Azure Key Vault with in-memory caching.

        NEVER logs or writes secret values to disk.

        Args:
            secret_name: Name of the Key Vault secret.

        Returns:
            Secret string value.

        Raises:
            KeyVaultError: If vault URL is not configured or retrieval fails.
        """
        if secret_name in self._cache:
            return self._cache[secret_name]

        if not self._vault_url:
            raise KeyVaultError("AZURE_KEY_VAULT_URL is not configured.")

        logger.info("Retrieving secret from Key Vault: secret_name=%s", secret_name)
        client = self._get_client()

        try:
            from azure.core.exceptions import ResourceNotFoundError

            secret = client.get_secret(secret_name)
            if not secret.value:
                raise KeyVaultError(f"Secret '{secret_name}' in Key Vault is empty.")

            self._cache[secret_name] = secret.value
            logger.info("Successfully retrieved and cached secret: secret_name=%s", secret_name)
            return secret.value
        except KeyVaultError:
            raise
        except Exception as exc:
            from azure.core.exceptions import ResourceNotFoundError

            if isinstance(exc, ResourceNotFoundError):
                raise KeyVaultError(f"Secret '{secret_name}' not found in Key Vault.") from exc
            logger.error(
                "Error retrieving secret from Key Vault: secret_name=%s error=%s",
                secret_name,
                type(exc).__name__,
            )
            raise KeyVaultError("Failed to retrieve secret from Azure Key Vault.") from exc

    def get_private_key_pem(self, secret_name: str = "alteryx-license-private-key") -> bytes:
        """Retrieve private key secret as UTF-8 bytes."""
        secret_str = self.get_secret(secret_name)
        return secret_str.encode("utf-8")

    def clear_cache(self) -> None:
        """Clear cached secrets from memory."""
        self._cache.clear()
