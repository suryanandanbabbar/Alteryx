"""Custom exception hierarchy for the License API Server.

Ensures internal implementation details, secret values, or Key Vault errors
are never leaked in exception messages or HTTP responses.
"""

from __future__ import annotations


class LicenseServerError(Exception):
    """Base exception for all License Server errors."""


class LicenseNotFoundError(LicenseServerError):
    """Raised when a requested license ID does not exist."""


class LicenseValidationError(LicenseServerError):
    """Raised when request parameters do not match license constraints."""


class LicenseConfigurationError(LicenseServerError):
    """Raised when server environment configuration is missing or invalid."""


class AuthenticationError(LicenseServerError):
    """Raised when API client authentication fails."""


class KeyVaultError(LicenseServerError):
    """Raised when retrieving or loading the private signing key fails."""


class SigningError(LicenseServerError):
    """Raised when computing the cryptographic Ed25519 signature fails."""
