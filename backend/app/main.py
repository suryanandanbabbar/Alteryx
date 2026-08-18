"""FastAPI application main entrypoint for AWA (Alteryx Workflow Analyzer)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.upload import router as upload_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.download import router as download_router
from backend.app.services.storage import get_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    storage = get_storage()
    yield
    # Shutdown
    storage.cleanup()


app = FastAPI(
    title="AWA — Alteryx Workflow Analyzer & Python Translator API",
    description="Deterministic static analysis and Python/pandas translation for Alteryx workflows.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers under /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(download_router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Welcome to AWA — Alteryx Workflow Analyzer API",
        "docs": "/docs",
        "health": "/api/health",
    }
