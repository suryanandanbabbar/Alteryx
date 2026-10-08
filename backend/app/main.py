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

# ─────────────────────────────────────────────────────────────────────
# Frontend serving
# ─────────────────────────────────────────────────────────────────────

# Source deployment:
#   project/
#   ├── backend/app/main.py
#   └── frontend/dist/
#
# Protected Nuitka deployment:
#   app-root/
#   ├── backend/app.cpython-311-...so
#   └── frontend/dist/
#
# Resolve both layouts without hard-coding an absolute path.

_THIS_FILE = Path(__file__).resolve()

_FRONTEND_CANDIDATES = [
    # Source layout:
    _THIS_FILE.parents[2] / "frontend" / "dist",

    # Protected Nuitka layout:
    _THIS_FILE.parents[1] / "frontend" / "dist",

    # Databricks application working directory fallback:
    Path.cwd() / "frontend" / "dist",
]

FRONTEND_DIST = next(
    (path for path in _FRONTEND_CANDIDATES if path.is_dir()),
    _FRONTEND_CANDIDATES[0],
)

FRONTEND_ASSETS = FRONTEND_DIST / "assets"

logger.info("Frontend distribution directory: %s", FRONTEND_DIST)
logger.info("Frontend assets directory: %s", FRONTEND_ASSETS)

if not FRONTEND_DIST.exists():
    logger.warning(
        "Frontend distribution directory not found: %s",
        FRONTEND_DIST,
    )

if not (FRONTEND_DIST / "index.html").exists():
    logger.warning(
        "Frontend index.html not found: %s",
        FRONTEND_DIST / "index.html",
    )

if not FRONTEND_ASSETS.exists():
    logger.warning(
        "Frontend assets directory not found: %s",
        FRONTEND_ASSETS,
    )


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the React application entry point."""
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


# Serve React/Vite static assets.
#
# This must be registered after the /api routers above.
# It handles requests such as:
#
#   /assets/index-CnBeFMZH.js
#   /assets/index-Cg9EKLLw.css
#
if FRONTEND_ASSETS.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_ASSETS)),
        name="frontend-assets",
    )