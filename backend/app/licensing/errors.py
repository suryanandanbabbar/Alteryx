"""License subsystem exception hierarchy.

All license-related exceptions inherit from LicenseError,
enabling catch-all handling at the application boundary.
"""

from __future__ import annotations


class LicenseError(Exception):
    """Base exception for all license-related errors."""
    pass


class LicenseConfigurationError(LicenseError):
    """Raised when license configuration is missing or invalid."""
    pass


class LicenseSecretError(LicenseError):
    """Raised when the Databricks license secret cannot be retrieved or is empty."""
    pass


class LicenseSignatureError(LicenseError):
    """Raised when Ed25519 signature verification fails."""
    pass


class LicenseExpiredError(LicenseError):
    """Raised when the license has expired."""
    pass


class LicenseRevokedError(LicenseError):
    """Raised when the license has been revoked."""
    pass


class LicenseInvalidError(LicenseError):
    """Raised when the license artifact is malformed, has invalid types, or mismatches identity."""
    pass


# Backward compatibility aliases
LicenseNetworkError = LicenseSecretError
LicenseAuthenticationError = LicenseInvalidError
