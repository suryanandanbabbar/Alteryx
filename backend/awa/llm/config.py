"""Azure Llama and LLM configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMConfig:
    """LLM client and deployment configuration."""
    endpoint: str = ""
    api_key: str = ""
    deployment: str = ""
    deployment_name: str = ""
    temperature: float = 0.0
    timeout: float = 15.0
    max_tokens: int = 500
    enabled: bool = True

    @classmethod
    def from_env(cls) -> LLMConfig:
        endpoint = os.getenv("AZURE_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_LLAMAKEY", "").strip()
        deployment = os.getenv("AZURE_DEPLOYMENT", "").strip()
        deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "").strip() or deployment

        try:
            temp = float(os.getenv("AWA_LLM_TEMPERATURE", "0.0"))
        except ValueError:
            temp = 0.0

        try:
            timeout = float(os.getenv("AWA_LLM_TIMEOUT", "15.0"))
        except ValueError:
            timeout = 15.0

        try:
            max_tokens = int(os.getenv("AWA_LLM_MAX_TOKENS", "500"))
        except ValueError:
            max_tokens = 500

        enabled_str = os.getenv("AWA_LLM_ENABLED", "true").lower()
        is_enabled = enabled_str not in ("false", "0", "no", "off")

        # Config is active only when endpoint and api_key are provided
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
        model_name = self.deployment_name or self.deployment or "NONE"
        return (
            f"LLMConfig(endpoint='{self.endpoint}', deployment='{model_name}', "
            f"api_key={has_key}, enabled={self.enabled}, temperature={self.temperature})"
        )
