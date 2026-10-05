"""Azure-hosted License API Server Module.

Provides authoritative Ed25519-signed lease generation backed by Azure Key Vault.
Operates as an independent, standalone service deployed to Azure App Service.
"""

from __future__ import annotations

__version__ = "1.0.0"
