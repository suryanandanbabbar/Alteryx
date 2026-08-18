"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "AWA Alteryx Converter API", "version": "1.0.0"}
