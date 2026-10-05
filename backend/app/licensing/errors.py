"""License subsystem exception hierarchy.

All license-related exceptions inherit from LicenseError,
enabling catch-all handling at the application boundary.
"""


class LicenseError(Exception):
    """Base exception for all license-related errors."""
    pass


class LicenseConfigurationError(LicenseError):
    """Raised when license configuration is missing or invalid."""
    pass


class LicenseNetworkError(LicenseError):
    """Raised when the Azure License API is unreachable."""
    pass


class LicenseAuthenticationError(LicenseError):
    """Raised when API client authentication fails (HTTP 401/403)."""
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
    """Raised when the license response is malformed or status is unrecognised."""
    pass
