"""Public application configuration endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from backend.app.config import get_settings
from backend.app.models.schemas import AppConfigDTO

router = APIRouter(tags=["Config"])


@router.get("/config", response_model=AppConfigDTO)
def get_public_config() -> AppConfigDTO:
    """Return public application configuration for the frontend."""
    current_settings = get_settings()
    return AppConfigDTO(
        code_based_workflows_url=current_settings.code_based_workflows_url,
        kpi_ontology_bank_url=current_settings.kpi_ontology_bank_url,
    )

