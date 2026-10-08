"""License configuration loaded from package-local developer_config.json.

In production, licensing validates a signed artifact retrieved from
a configured secret scope using the embedded Ed25519 public verification key.
All application-specific settings are loaded from:
    backend/app/licensing/developer_config.json
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from .errors import LicenseConfigurationError

if TYPE_CHECKING:
    from .usage_source import UsageDataSource
    from .developer_config import DeveloperLicenseConfig

logger = logging.getLogger("awa.licensing.config")

# ---------------------------------------------------------------------------
# Canonical Embedded Verification Key (Cryptographic Trust Anchor)
# ---------------------------------------------------------------------------
# Production Ed25519 public key (base64-encoded, 32 bytes).
# The corresponding private key resides exclusively in the private signing
# Azure Key Vault and is NEVER included in client or runtime builds.
_EMBEDDED_PUBLIC_KEY: str = "aykIwjC0U0mxmTXUDhQdwBCiogj8YRNWy/8EieAfx9s="


def _get_dev_config(config_path: Path | None = None) -> DeveloperLicenseConfig | None:
    try:
        from .developer_config import DeveloperLicenseConfig
        return DeveloperLicenseConfig.load_from_file(config_path)
    except Exception as exc:
        logger.debug("Could not load developer_config.json: %s", exc)
        return None


@dataclass(frozen=True)
class LicenseConfig:
    """Immutable license configuration.

    Application coordinates and enforcement policies default to the
    package-local `developer_config.json`. EXL developers can also configure
    or inject custom parameters programmatically.
    """

    secret_scope: str | None = None
    secret_name: str | None = None
    license_id: str | None = None
    product: str | None = None
    environment: str | None = None
    public_key_b64: str = _EMBEDDED_PUBLIC_KEY

    # Criteria flags: strictly int 0 or 1
    date_enabled: int | None = None
    volume_enabled: int | None = None
    token_usage_enabled: int | None = None

    # Limits
    volume_limit: int | None = None
    token_usage_limit: int | None = None

    # Optional usage sources
    volume_usage_source: UsageDataSource | None = None
    token_usage_source: UsageDataSource | None = None

    def __post_init__(self) -> None:
        dev_cfg = _get_dev_config()

        if self.secret_scope is None:
            object.__setattr__(self, "secret_scope", dev_cfg.artifact_secret.secret_scope if dev_cfg else "")
        if self.secret_name is None:
            object.__setattr__(self, "secret_name", dev_cfg.artifact_secret.secret_name if dev_cfg else "")
        if self.license_id is None:
            object.__setattr__(self, "license_id", dev_cfg.identity.license_id if dev_cfg else "")
        if self.product is None:
            object.__setattr__(self, "product", dev_cfg.identity.product if dev_cfg else "")
        if self.environment is None:
            object.__setattr__(self, "environment", dev_cfg.identity.environment if dev_cfg else "")

        if self.date_enabled is None:
            object.__setattr__(self, "date_enabled", dev_cfg.enforcement.date_enabled if dev_cfg else 1)
        if self.volume_enabled is None:
            object.__setattr__(self, "volume_enabled", dev_cfg.enforcement.volume_enabled if dev_cfg else 0)
        if self.token_usage_enabled is None:
            object.__setattr__(self, "token_usage_enabled", dev_cfg.enforcement.token_usage_enabled if dev_cfg else 0)

        if self.volume_limit is None:
            object.__setattr__(self, "volume_limit", dev_cfg.volume.volume_limit if dev_cfg else 0)
        if self.token_usage_limit is None:
            object.__setattr__(self, "token_usage_limit", dev_cfg.token_usage.token_usage_limit if dev_cfg else 0)

    @property
    def enabled(self) -> bool:
        """Licensing is permanently enabled in production."""
        return True

    @classmethod
    def load(cls, config_path: Path | None = None) -> LicenseConfig:
        """Load configuration explicitly from package-local or custom developer_config.json."""
        from .developer_config import DeveloperLicenseConfig
        dev_cfg = DeveloperLicenseConfig.load_from_file(config_path)
        return cls(
            secret_scope=dev_cfg.artifact_secret.secret_scope,
            secret_name=dev_cfg.artifact_secret.secret_name,
            license_id=dev_cfg.identity.license_id,
            product=dev_cfg.identity.product,
            environment=dev_cfg.identity.environment,
            public_key_b64=_EMBEDDED_PUBLIC_KEY,
            date_enabled=dev_cfg.enforcement.date_enabled,
            volume_enabled=dev_cfg.enforcement.volume_enabled,
            token_usage_enabled=dev_cfg.enforcement.token_usage_enabled,
            volume_limit=dev_cfg.volume.volume_limit,
            token_usage_limit=dev_cfg.token_usage.token_usage_limit,
        )

    @classmethod
    def from_env(cls) -> LicenseConfig:
        """Backward-compatible entry point delegating to package-local configuration."""
        return cls.load()

    def validate(self) -> None:
        """Raise :class:`LicenseConfigurationError` if required fields are missing or invalid."""
        if not self.secret_scope:
            raise LicenseConfigurationError("Secret scope is required.")
        if not self.secret_name:
            raise LicenseConfigurationError("Secret name is required.")
        if not self.license_id:
            raise LicenseConfigurationError("License ID is required.")
        if not self.product:
            raise LicenseConfigurationError("Product is required.")
        if not self.environment:
            raise LicenseConfigurationError("Environment is required.")
        if not self.public_key_b64:
            raise LicenseConfigurationError(
                "Ed25519 public key is required. Embed the production public key in the build."
            )

        # Flag type validation: strictly int 0 or 1 if provided
        for flag_name, flag_val in (
            ("date_enabled", self.date_enabled),
            ("volume_enabled", self.volume_enabled),
            ("token_usage_enabled", self.token_usage_enabled),
        ):
            if flag_val is not None and (type(flag_val) is not int or flag_val not in (0, 1)):
                raise LicenseConfigurationError(
                    f"Configuration criteria flag '{flag_name}' must be strictly 0 or 1 (got {flag_val!r})."
                )

        # Limit validation if provided: must be non-negative integer
        if self.volume_limit is not None and (type(self.volume_limit) is not int or self.volume_limit < 0):
            raise LicenseConfigurationError(
                f"Volume limit must be a non-negative integer, got {self.volume_limit!r}."
            )
        if self.token_usage_limit is not None and (type(self.token_usage_limit) is not int or self.token_usage_limit < 0):
            raise LicenseConfigurationError(
                f"Token usage limit must be a non-negative integer, got {self.token_usage_limit!r}."
            )
