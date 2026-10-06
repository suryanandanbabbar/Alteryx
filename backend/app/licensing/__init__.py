"""AWA License Enforcement Module.

Databricks Key Vault-backed Ed25519 signed license validation.
"""

from .config import LicenseConfig
from .errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseSecretError,
    LicenseSignatureError,
)
from .manager import LicenseManager
from .models import LicenseArtifact, LicenseState
from .secret_provider import DatabricksSecretProvider, InMemorySecretProvider, SecretProvider

__all__ = [
    "LicenseConfig",
    "LicenseManager",
    "SecretProvider",
    "DatabricksSecretProvider",
    "InMemorySecretProvider",
    "LicenseArtifact",
    "LicenseState",
    "LicenseConfigurationError",
    "LicenseSecretError",
    "LicenseSignatureError",
    "LicenseExpiredError",
    "LicenseInvalidError",
]
