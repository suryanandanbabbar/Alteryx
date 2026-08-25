"""Azure Llama and LLM configuration management.

Environment variables are read at runtime. No credentials are stored in code.
The project .env file (if present) is loaded for local development convenience.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("awa.llm")


def _find_project_dotenv() -> str | None:
    """Locate the project root .env file by walking up from this module's directory."""
    # Walk up from backend/awa/llm/ → backend/awa/ → backend/ → project root
    current = Path(__file__).resolve().parent
    for _ in range(6):  # Max 6 levels up
        candidate = current / ".env"
        if candidate.is_file():
            return str(candidate)
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_dotenv_if_available() -> None:
    """Load .env from project root if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
        dotenv_path = _find_project_dotenv()
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=False)
            logger.debug("Loaded .env from %s", dotenv_path)
        else:
            # Fall back to default dotenv search
            load_dotenv(override=False)
    except ImportError:
        pass


# Load .env once on module import
_load_dotenv_if_available()


@dataclass
class LLMConfig:
    """LLM client and deployment configuration.
    
    All credentials are read from environment variables at runtime.
    No secrets are stored in source code or configuration files.
    """
    endpoint: str = ""
    api_key: str = ""
    deployment: str = ""
    deployment_name: str = ""
    temperature: float = 0.0
    timeout: float = 30.0
    max_tokens: int = 500
    enabled: bool = True

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create LLM configuration from runtime environment variables."""
        endpoint = os.getenv("AZURE_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_LLAMAKEY", "").strip()
        deployment = os.getenv("AZURE_DEPLOYMENT", "").strip()
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "").strip() or deployment

        try:
            temp = float(os.getenv("AWA_LLM_TEMPERATURE", "0.0"))
        except ValueError:
            temp = 0.0

        try:
            timeout = float(os.getenv("AWA_LLM_TIMEOUT", "30.0"))
        except ValueError:
            timeout = 30.0

        try:
            max_tokens = int(os.getenv("AWA_LLM_MAX_TOKENS", "500"))
        except ValueError:
            max_tokens = 500

        enabled_str = os.getenv("AWA_LLM_ENABLED", "true").lower()
        is_enabled = enabled_str not in ("false", "0", "no", "off")

        # Config is active only when all required credentials are provided
        has_credentials = bool(endpoint and api_key and (deployment or deployment_name))
        active = is_enabled and has_credentials

        return cls(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            deployment_name=deployment_name,
            temperature=temp,
            timeout=timeout,
            max_tokens=max_tokens,
            enabled=active,
        )

    def is_available(self) -> bool:
        """Check if LLM configuration has all required values and is enabled."""
        return bool(self.enabled and self.endpoint and self.api_key and (self.deployment or self.deployment_name))

    def safe_repr(self) -> str:
        """Safe string representation that never exposes API keys or secrets."""
        has_key = f"SET (len={len(self.api_key)})" if self.api_key else "NOT SET"
        has_endpoint = "SET" if self.endpoint else "NOT SET"
        model_name = self.deployment_name or self.deployment or "NONE"
        return (
            f"LLMConfig(endpoint={has_endpoint}, deployment='{model_name}', "
            f"api_key={has_key}, enabled={self.enabled}, temperature={self.temperature})"
        )


def initialize_llm() -> None:
    """Initialize the LLM subsystem at application startup.
    
    Reads runtime environment, configures the global LLM client,
    and logs sanitized configuration status. Never logs secrets.
    """
    from .client import AzureLlamaClient, set_default_llm_client
    from .generator import LLMNarrativeGenerator, set_default_generator
    from .cache import get_global_narrative_cache

    config = LLMConfig.from_env()

    if config.is_available():
        client = AzureLlamaClient(config=config)
        set_default_llm_client(client)
        generator = LLMNarrativeGenerator(client=client, cache=get_global_narrative_cache())
        set_default_generator(generator)
        logger.info(
            "LLM provider: Azure | configuration: available | deployment: %s",
            config.deployment_name or config.deployment,
        )
    else:
        logger.info(
            "LLM provider: Azure | configuration: unavailable | fallback: deterministic | config: %s",
            config.safe_repr(),
        )
