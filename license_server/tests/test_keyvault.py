"""Tests for AzureKeyVaultClient secret management and caching.

Verifies that the private key is retrieved securely, cached in memory,
and errors are handled without exposing sensitive data.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError

from license_server.errors import KeyVaultError
from license_server.keyvault import AzureKeyVaultClient


def test_keyvault_empty_url_raises_error():
    """Attempting to fetch a secret with an empty vault URL must raise KeyVaultError."""
    client = AzureKeyVaultClient(vault_url="")
    with pytest.raises(KeyVaultError) as exc_info:
        client.get_secret("test-secret")
    assert "AZURE_KEY_VAULT_URL is not configured" in str(exc_info.value)


def test_keyvault_secret_caching():
    """Secrets must be cached after first retrieval to avoid repeated Key Vault network calls."""
    client = AzureKeyVaultClient(vault_url="https://test-vault.vault.azure.net")

    mock_secret = MagicMock()
    mock_secret.value = "cached-secret-value-12345"

    mock_secret_client = MagicMock()
    mock_secret_client.get_secret.return_value = mock_secret
    client._client = mock_secret_client

    # First call: retrieves from SecretClient
    val1 = client.get_secret("my-secret")
    assert val1 == "cached-secret-value-12345"
    assert mock_secret_client.get_secret.call_count == 1

    # Second call: served from memory cache
    val2 = client.get_secret("my-secret")
    assert val2 == "cached-secret-value-12345"
    assert mock_secret_client.get_secret.call_count == 1

    # After clearing cache: calls SecretClient again
    client.clear_cache()
    val3 = client.get_secret("my-secret")
    assert val3 == "cached-secret-value-12345"
    assert mock_secret_client.get_secret.call_count == 2


def test_keyvault_not_found_handling():
    """Missing secret in Key Vault must raise KeyVaultError."""
    client = AzureKeyVaultClient(vault_url="https://test-vault.vault.azure.net")

    mock_secret_client = MagicMock()
    mock_secret_client.get_secret.side_effect = ResourceNotFoundError("Secret not found")
    client._client = mock_secret_client

    with pytest.raises(KeyVaultError) as exc_info:
        client.get_secret("non-existent-secret")
    assert "Secret 'non-existent-secret' not found" in str(exc_info.value)


def test_keyvault_network_error_handling():
    """Network failure accessing Key Vault must raise KeyVaultError."""
    client = AzureKeyVaultClient(vault_url="https://test-vault.vault.azure.net")

    mock_secret_client = MagicMock()
    mock_secret_client.get_secret.side_effect = ServiceRequestError("Connection timeout")
    client._client = mock_secret_client

    with pytest.raises(KeyVaultError) as exc_info:
        client.get_secret("my-secret")
    assert "Failed to retrieve secret" in str(exc_info.value)
