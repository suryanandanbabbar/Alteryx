"""License repository abstraction and environment-backed implementation.

Provides decoupling between license persistence (database/Cosmos DB/Postgres)
and the validation service layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from .config import ServerConfig
from .models import LicenseRecord, LicenseStatus


class LicenseRepository(ABC):
    """Abstract interface for license storage and retrieval."""

    @abstractmethod
    def get_license(self, license_id: str) -> LicenseRecord | None:
        """Retrieve a license record by its unique identifier.

        Args:
            license_id: Customer or tenant license identifier.

        Returns:
            LicenseRecord if found, or None if unknown.
        """
        ...


class EnvironmentLicenseRepository(LicenseRepository):
    """Environment-backed repository for standalone operation and testing.

    Populates default license from ServerConfig/environment variables and
    supports in-memory additions for testing.
    """

    def __init__(self, config: ServerConfig | None = None) -> None:
        """Initialize repository with configured default license."""
        self._config = config or ServerConfig.from_env()
        self._licenses: Dict[str, LicenseRecord] = {}

        if self._config.default_license_id:
            status_enum = LicenseStatus(self._config.default_status)
            self._licenses[self._config.default_license_id] = LicenseRecord(
                license_id=self._config.default_license_id,
                product=self._config.default_product,
                environment=self._config.default_environment,
                status=status_enum,
                expires_at=self._config.default_expiry,
                features=self._config.default_features,
            )

    def add_license(self, record: LicenseRecord) -> None:
        """Register or override a license in memory (useful for testing)."""
        self._licenses[record.license_id] = record

    def get_license(self, license_id: str) -> LicenseRecord | None:
        """Look up license record by license_id."""
        return self._licenses.get(license_id)
