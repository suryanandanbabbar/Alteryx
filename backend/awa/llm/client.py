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

    @property
    def is_available(self) -> bool:
        """Whether this client can make real LLM requests."""
        return True


class AzureLlamaClient(LLMClient):
    """Client for Azure-hosted Llama and OpenAI-compatible inference endpoints.
    
    Supports:
    - Azure OpenAI endpoints (*.openai.azure.com)
    - Azure AI Foundry / Model Inference / Serverless MaaS endpoints
    - Direct OpenAI-compatible chat/completions endpoints
    
    Authentication is determined by endpoint type:
    - Azure OpenAI: uses 'api-key' header
    - Azure AI Foundry / MaaS: uses 'Authorization: Bearer' header
    - Direct endpoints: uses 'Authorization: Bearer' header
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    @property
    def model_name(self) -> str:
        return self.config.deployment_name or self.config.deployment or "azure-llama"

    @property
    def is_available(self) -> bool:
        return self.config.is_available()

    def _resolve_url(self) -> str:
        """Resolve full API URL from Azure endpoint configuration."""
        endpoint = self.config.endpoint.strip()
        if not endpoint:
            return ""

        # Direct full completion path provided
        if "/chat/completions" in endpoint:
            return endpoint

        # Azure OpenAI style: https://resource.openai.azure.com
        if "openai.azure.com" in endpoint:
            deployment = self.config.deployment_name or self.config.deployment or "Llama"
            base = endpoint.rstrip("/")
            return f"{base}/openai/deployments/{deployment}/chat/completions?api-version=2024-06-01"

        # Azure AI Foundry / Model Inference / Serverless MaaS endpoint
        # These typically end with /v1 or /models or just the base URL
        base = endpoint.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        if base.endswith("/models"):
            return f"{base}/chat/completions"

        # Default: append /v1/chat/completions for standard inference endpoints
        return f"{base}/v1/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with the correct auth scheme for the endpoint type."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }

        endpoint = self.config.endpoint.strip()

        if "openai.azure.com" in endpoint:
            # Azure OpenAI uses api-key header
            headers["api-key"] = self.config.api_key
        else:
            # Azure AI Foundry / MaaS / standard endpoints use Bearer auth
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        return headers

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Execute chat completion request against Azure endpoint with robust error handling."""
        if not self.config.is_available():
            logger.debug("Azure LLM client unavailable — missing runtime credentials")
            return None

        url = self._resolve_url()
        if not url:
            logger.warning("LLM generation failed: could not resolve Azure endpoint URL")
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

        # Include model parameter for endpoints that require it
        model = self.config.deployment_name or self.config.deployment
        if model:
            payload["model"] = model

        headers = self._build_headers()

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
                    logger.warning(
                        "LLM generation failed: HTTP %d from Azure endpoint",
                        status,
                    )
                    return None
                resp_bytes = response.read()
                data = json.loads(resp_bytes.decode("utf-8", errors="replace"))

            # Parse standard chat completion format
            choices = data.get("choices", [])
            if not choices:
                logger.warning("LLM generation failed: response contained no choices")
                return None

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = message.get("content") or ""

            return str(content).strip() if content else None

        except urllib.error.HTTPError as e:
            # Read error body for diagnosis but never log secrets
            error_body = ""
            try:
                error_body = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            # Sanitize: remove any potential credential echoes from error body
            sanitized_body = error_body
            if self.config.api_key and len(self.config.api_key) > 8:
                sanitized_body = sanitized_body.replace(self.config.api_key, "[REDACTED]")
            logger.warning(
                "LLM generation failed: HTTP %s — %s | body: %s",
                getattr(e, "code", "UNKNOWN"),
                getattr(e, "reason", "UNKNOWN"),
                sanitized_body[:200] if sanitized_body else "(empty)",
            )
            return None
        except urllib.error.URLError as e:
            logger.warning(
                "LLM generation failed: connection error — %s",
                getattr(e, "reason", "Connection failed"),
            )
            return None
        except TimeoutError:
            logger.warning(
                "LLM generation failed: request timed out after %.1fs",
                self.config.timeout,
            )
            return None
        except Exception as e:
            logger.warning(
                "LLM generation failed: unexpected error — %s",
                type(e).__name__,
            )
            return None

    def diagnose(self) -> dict[str, Any]:
        """Return a sanitized diagnostic result for the Azure LLM configuration.
        
        Never returns secrets or credentials.
        """
        result: dict[str, Any] = {
            "endpoint_configured": bool(self.config.endpoint),
            "deployment_configured": bool(self.config.deployment or self.config.deployment_name),
            "key_configured": bool(self.config.api_key),
            "model": self.config.deployment_name or self.config.deployment or "NONE",
            "enabled": self.config.enabled,
            "available": self.config.is_available(),
        }

        if not self.config.is_available():
            result["status"] = "unavailable"
            result["reason"] = "missing_credentials" if not self.config.api_key else "disabled"
            return result

        # Attempt a minimal test request
        try:
            test_response = self.generate(
                system_prompt="Respond with exactly: OK",
                user_prompt="Test",
                max_tokens=5,
            )
            if test_response:
                result["status"] = "success"
                result["response_length"] = len(test_response)
            else:
                result["status"] = "failed"
                result["reason"] = "empty_response"
        except Exception as e:
            result["status"] = "failed"
            result["reason"] = type(e).__name__

        return result


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

    @property
    def is_available(self) -> bool:
        return True

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
