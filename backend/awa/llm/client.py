"""LLM client abstraction, Azure Llama provider, and mock test client."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable
import urllib.request
import urllib.error

from .config import LLMConfig

logger = logging.getLogger("awa.llm")


class LLMClient(ABC):
    """Abstract interface for LLM completion services."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Generate text completion from system and user prompts.

        Returns:
            Generated text content, or None if generation failed.
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the active model or deployment."""
        ...


class AzureLlamaClient(LLMClient):
    """Client for Azure-hosted Llama and OpenAI-compatible inference endpoints."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    @property
    def model_name(self) -> str:
        return self.config.deployment_name or self.config.deployment or "azure-llama"

    def _resolve_url(self) -> str:
        """Resolve full API URL from Azure endpoint configuration."""
        endpoint = self.config.endpoint.strip()
        if not endpoint:
            return ""

        # Direct full completion path provided
        if endpoint.endswith("/chat/completions") or endpoint.endswith("/v1/chat/completions"):
            return endpoint

        # Azure OpenAI style: https://resource.openai.azure.com
        if "openai.azure.com" in endpoint:
            deployment = self.config.deployment_name or self.config.deployment or "Llama"
            return f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version=2024-06-01"

        # Azure AI Studio / Model Inference / Serverless MaaS endpoint
        if endpoint.endswith("/models"):
            return f"{endpoint}/chat/completions"

        return f"{endpoint.rstrip('/')}/chat/completions"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Execute chat completion request against Azure endpoint with robust error handling."""
        if not self.config.is_available():
            logger.debug("Azure LLM client unavailable or missing credentials")
            return None

        url = self._resolve_url()
        if not url:
            logger.warning("Failed to resolve Azure LLM endpoint URL")
            return None

        temp = temperature if temperature is not None else self.config.temperature
        tokens = max_tokens if max_tokens is not None else self.config.max_tokens

        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temp,
            "max_tokens": tokens,
        }

        # Some Azure endpoints require the model parameter
        model = self.config.deployment_name or self.config.deployment
        if model:
            payload["model"] = model

        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key,
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            req_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url=url,
                data=req_bytes,
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                status = response.status
                if status != 200:
                    logger.warning("Azure LLM responded with HTTP status %d", status)
                    return None
                resp_bytes = response.read()
                data = json.loads(resp_bytes.decode("utf-8", errors="replace"))

            # Parse standard chat completion format
            choices = data.get("choices", [])
            if not choices:
                logger.warning("Azure LLM response had no choices")
                return None

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content") or ""

            return str(content).strip() if content else None

        except urllib.error.HTTPError as e:
            # Never log secrets or authorization headers
            logger.warning("Azure LLM HTTP error: status=%s, reason=%s", getattr(e, "code", "UNKNOWN"), getattr(e, "reason", "UNKNOWN"))
            return None
        except urllib.error.URLError as e:
            logger.warning("Azure LLM connection error: %s", getattr(e, "reason", "Connection failed"))
            return None
        except TimeoutError:
            logger.warning("Azure LLM request timed out after %.1fs", self.config.timeout)
            return None
        except Exception as e:
            logger.warning("Azure LLM unexpected error: %s", type(e).__name__)
            return None


class FakeLLMClient(LLMClient):
    """In-memory mock client for unit testing and deterministic simulation."""

    def __init__(
        self,
        default_response: str = "Mock generated narrative.",
        response_map: dict[str, str] | None = None,
        generator_fn: Callable[[str, str], str | None] | None = None,
        model_name: str = "mock-llama",
    ) -> None:
        self.default_response = default_response
        self.response_map = response_map or {}
        self.generator_fn = generator_fn
        self._model_name = model_name
        self.calls: list[dict[str, Any]] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self.generator_fn:
            return self.generator_fn(system_prompt, user_prompt)

        for match_key, resp in self.response_map.items():
            if match_key.lower() in user_prompt.lower() or match_key.lower() in system_prompt.lower():
                return resp

        return self.default_response


# Global client instance
_global_client: LLMClient | None = None


def get_default_llm_client() -> LLMClient:
    """Get the active LLM client instance (AzureLlamaClient by default)."""
    global _global_client
    if _global_client is None:
        _global_client = AzureLlamaClient()
    return _global_client


def set_default_llm_client(client: LLMClient | None) -> None:
    """Override the active LLM client (useful for tests)."""
    global _global_client
    _global_client = client
