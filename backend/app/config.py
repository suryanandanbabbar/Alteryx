"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pydantic import BaseModel, Field


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


settings = Settings()
