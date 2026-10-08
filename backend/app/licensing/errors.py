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


class LicenseLimitExceededError(LicenseError):
    """Raised when a configurable license limit (volume, token usage, etc.) has been reached or exceeded."""

    def __init__(
        self,
        criterion: str,
        current: int | None = None,
        limit: int | None = None,
        license_id: str = "",
        message: str = "",
    ) -> None:
        self.criterion = criterion
        self.current = current
        self.limit = limit
        self.license_id = license_id
        if not message:
            criterion_label = criterion.replace("_", " ").capitalize()
            if current is not None and limit is not None:
                message = f"{criterion_label} license limit reached: {current}/{limit}."
            else:
                message = f"{criterion_label} license limit reached."
        super().__init__(message)


# Backward compatibility aliases
LicenseNetworkError = LicenseSecretError
LicenseAuthenticationError = LicenseInvalidError
