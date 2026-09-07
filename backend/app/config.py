"""Application configuration loaded from environment variables and .env file."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("awa.config")


def _find_project_dotenv() -> Path | None:
    """Locate the project root .env file by walking up from this directory."""
    current = Path(__file__).resolve().parent
    for _ in range(6):  # Max 6 levels up
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_dotenv_if_available() -> None:
    """Load .env from project root into os.environ with override=False (process env takes precedence)."""
    dotenv_path = _find_project_dotenv()
    try:
        from dotenv import load_dotenv

        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path, override=False)
            logger.debug("Loaded .env from %s", dotenv_path)
        else:
            load_dotenv(override=False)
    except ImportError:
        # Fallback manual line parser if python-dotenv is not available
        if dotenv_path and dotenv_path.is_file():
            try:
                for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
            except Exception:
                pass


# Load .env once on module import
_load_dotenv_if_available()


def validate_code_based_workflows_url(url: str | None) -> str | None:
    """Validate that the configured Code-Based Workflows URL is a valid HTTP/HTTPS URL."""
    if url is None:
        return None
    trimmed = str(url).strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Invalid CODE_BASED_WORKFLOWS_URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."
        )
    if not parsed.netloc and not parsed.hostname:
        raise ValueError(
            f"Invalid CODE_BASED_WORKFLOWS_URL '{trimmed}'. A valid hostname is required."
        )
    return trimmed


def validate_kpi_ontology_bank_url(url: str | None) -> str | None:
    """Validate that the configured KPI Ontology Bank URL is a valid HTTP/HTTPS URL."""
    if url is None:
        return None
    trimmed = str(url).strip()
    if not trimmed:
        return None
    parsed = urlparse(trimmed)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(
            f"Invalid KPI_ONTOLOGY_BANK_URL scheme '{parsed.scheme}'. Only 'http' and 'https' are allowed."
        )
    if not parsed.netloc and not parsed.hostname:
        raise ValueError(
            f"Invalid KPI_ONTOLOGY_BANK_URL '{trimmed}'. A valid hostname is required."
        )
    return trimmed


class Settings(BaseModel):
    """AWA server settings."""
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "AWA_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ]
    )
    max_upload_bytes: int = Field(
        default_factory=lambda: int(os.getenv("AWA_MAX_UPLOAD_BYTES", "52428800"))
    )
    storage_ttl_seconds: int = Field(
        default_factory=lambda: int(os.getenv("AWA_STORAGE_TTL_SECONDS", "3600"))
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("AWA_LOG_LEVEL", "INFO")
    )
    code_based_workflows_url: str | None = Field(
        default_factory=lambda: validate_code_based_workflows_url(
            os.getenv("CODE_BASED_WORKFLOWS_URL") or os.getenv("AWA_CODE_BASED_WORKFLOWS_URL")
        )
    )
    kpi_ontology_bank_url: str | None = Field(
        default_factory=lambda: validate_kpi_ontology_bank_url(
            os.getenv("KPI_ONTOLOGY_BANK_URL") or os.getenv("AWA_KPI_ONTOLOGY_BANK_URL")
        )
    )

    @field_validator("code_based_workflows_url", mode="after")
    @classmethod
    def check_code_based_url(cls, v: str | None) -> str | None:
        return validate_code_based_workflows_url(v)

    @field_validator("kpi_ontology_bank_url", mode="after")
    @classmethod
    def check_kpi_ontology_url(cls, v: str | None) -> str | None:
        return validate_kpi_ontology_bank_url(v)


def get_settings() -> Settings:
    """Return an updated settings instance."""
    return Settings()


settings = get_settings()

