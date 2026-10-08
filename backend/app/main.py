"""FastAPI application main entrypoint for AWA (Alteryx Workflow Analyzer)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

from backend.app.config import settings
from backend.app.api.health import router as health_router
from backend.app.api.config import router as config_router
from backend.app.api.upload import router as upload_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.download import router as download_router
from backend.app.api.portfolio import router as portfolio_router
from backend.app.services.storage import get_storage

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── License enforcement (before any other initialisation) ────────
    from backend.app.licensing import LicenseManager
    from backend.app.licensing.adapters import DatabricksSecretProvider

    license_mgr = LicenseManager(secret_provider=DatabricksSecretProvider())
    license_mgr.validate_or_raise()  # blocks startup if invalid

    # ── Existing startup ─────────────────────────────────────────────
    logger.info("Starting AWA application service.")
    storage = get_storage()
    # Initialize LLM subsystem — reads runtime environment for Azure credentials
    try:
        from backend.awa.llm.config import initialize_llm
        initialize_llm()
    except Exception as e:
        logger.warning("LLM initialization skipped: %s — %s",
                       type(e).__name__, str(e)[:200])
    yield
    # ── Shutdown ─────────────────────────────────────────────────────
    logger.info("Shutting down AWA application service.")
    storage.cleanup()


app = FastAPI(
    title="AWA — Alteryx Workflow Analyzer & Python Translator API",
    description="Deterministic static analysis and Python translation for Alteryx workflows.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routers under /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")

PROJECT_ROOT = Path(__file__).parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if not FRONTEND_DIST.exists():
    logger.warning("Frontend distribution directory not found: %s", FRONTEND_DIST)

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index_file = FRONTEND_DIST / "index.html"

    if not index_file.exists():
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend build not found.",
                "expected_path": str(index_file),
            },
        )
    return FileResponse(index_file)

@app.get("/")
def root():
    return {
        "service": "AWA Alteryx Converter API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }
