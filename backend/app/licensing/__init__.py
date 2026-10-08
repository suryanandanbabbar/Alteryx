"""AWA Universal Modular License Enforcement Module.

Databricks Key Vault-backed Ed25519 signed license validation with
configurable multi-criteria enforcement (Date, Volume, Token Usage).
"""

from .config import LicenseConfig
from .developer_config import DeveloperLicenseConfig
from .criteria import (
    CriterionResult,
    DateCriterion,
    LicenseCriterion,
    TokenUsageCriterion,
    VolumeCriterion,
)
from .errors import (
    LicenseConfigurationError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseLimitExceededError,
    LicenseSecretError,
    LicenseSignatureError,
)
from .manager import LicenseManager
from .models import (
    DatePolicy,
    LicenseArtifact,
    LicensePolicy,
    LicenseState,
    TokenUsagePolicy,
    VolumePolicy,
)
from .secret_provider import DatabricksSecretProvider, InMemorySecretProvider, SecretProvider
from .usage_source import CallableUsageDataSource, InMemoryUsageDataSource, UsageDataSource

__all__ = [
    "LicenseConfig",
    "DeveloperLicenseConfig",
    "LicenseManager",
    "SecretProvider",
    "DatabricksSecretProvider",
    "InMemorySecretProvider",
    "LicenseArtifact",
    "LicenseState",
    "DatePolicy",
    "VolumePolicy",
    "TokenUsagePolicy",
    "LicensePolicy",
    "LicenseCriterion",
    "CriterionResult",
    "DateCriterion",
    "VolumeCriterion",
    "TokenUsageCriterion",
    "UsageDataSource",
    "InMemoryUsageDataSource",
    "CallableUsageDataSource",
    "LicenseConfigurationError",
    "LicenseSecretError",
    "LicenseSignatureError",
    "LicenseExpiredError",
    "LicenseInvalidError",
    "LicenseLimitExceededError",
]
