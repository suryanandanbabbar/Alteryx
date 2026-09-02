"""Portfolio endpoints — query and upload multi-workflow portfolios."""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Any
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from awa.parser.format_handler import detect_format
from backend.app.config import settings
from backend.app.models.schemas import (
    AnalysisOverviewDTO,
    PortfolioOverviewDTO,
    PortfolioWorkflowSummaryDTO,
    RationalisationAnalysisDTO,
)
from backend.app.services.analyzer import to_overview_dto
from backend.app.services.portfolio_service import (
    SUPPORTED_WORKFLOW_EXTENSIONS,
    extract_workflows_from_zip,
    process_portfolio_uploads,
)
from backend.app.services.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


def _to_portfolio_dto(portfolio) -> PortfolioOverviewDTO:
    """Convert PortfolioAnalysis to PortfolioOverviewDTO."""
    return PortfolioOverviewDTO(**portfolio.to_dict())


@router.post("/upload", response_model=PortfolioOverviewDTO | AnalysisOverviewDTO)
async def upload_portfolio(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(None),
    portfolio_name: str = Form("ETL Portfolio"),
):
    """Upload multiple Alteryx workflows or folder packages to analyze as a portfolio.

    If exactly 1 workflow is discovered, returns AnalysisOverviewDTO (single-workflow mode).
    If multiple workflows are discovered, returns PortfolioOverviewDTO (portfolio mode).
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILES_MISSING", "error": "FILES_MISSING", "message": "No files uploaded."},
        )

    discovered_workflows: list[tuple[str, str, bytes]] = []

    for idx, f in enumerate(files):
        if not f.filename:
            continue

        filename = Path(f.filename).name
        # Skip macOS metadata or hidden files
        if filename.startswith(".") or "__MACOSX" in (f.filename or ""):
            continue

        rel_path = (relative_paths[idx] if relative_paths and idx < len(relative_paths) else f.filename) or filename

        # Read content with size guard
        content = await f.read()
        if not content:
            continue

        # Check if zip/package
        ext = Path(filename).suffix.lower()
        if ext in (".zip", ".yxzp") or (len(content) >= 4 and content[:4] == b"PK\x03\x04"):
            zip_discovered = extract_workflows_from_zip(content, base_prefix=Path(rel_path).parent.as_posix())
            discovered_workflows.extend(zip_discovered)
        elif ext in SUPPORTED_WORKFLOW_EXTENSIONS:
            fmt = detect_format(filename, content)
            if fmt in ("yxmd", "yxwz", "xml"):
                discovered_workflows.append((filename, rel_path, content))

    if not discovered_workflows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_WORKFLOWS_FOUND",
                "error": "NO_WORKFLOWS_FOUND",
                "message": "No valid Alteryx workflow files (.yxmd, .yxwz, .xml) found in the upload.",
            },
        )

    # Case A/D: Exactly one workflow found -> preserve existing single-workflow behavior
    if len(discovered_workflows) == 1:
        fname, rpath, bcontent = discovered_workflows[0]
        from backend.app.services.analyzer import process_uploaded_workflow
        res = process_uploaded_workflow(fname, bcontent)
        get_storage().save(res)
        return to_overview_dto(res)

    # Case B/C: Multiple workflows -> Portfolio mode
    portfolio = process_portfolio_uploads(discovered_workflows, portfolio_name=portfolio_name)
    return _to_portfolio_dto(portfolio)


@router.get("/{portfolio_id}", response_model=PortfolioOverviewDTO)
def get_portfolio(portfolio_id: str):
    """Retrieve full portfolio analysis by portfolio_id."""
    storage = get_storage()
    portfolio = storage.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio with ID '{portfolio_id}' not found or session has expired.",
        )
    return _to_portfolio_dto(portfolio)


@router.get("/{portfolio_id}/workflows", response_model=list[PortfolioWorkflowSummaryDTO])
def list_portfolio_workflows(portfolio_id: str):
    """List workflow summaries in a portfolio."""
    storage = get_storage()
    portfolio = storage.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio with ID '{portfolio_id}' not found or session has expired.",
        )
    return [PortfolioWorkflowSummaryDTO(**w.to_dict()) for w in portfolio.workflows]


@router.get("/{portfolio_id}/workflow/{workflow_id}", response_model=AnalysisOverviewDTO)
def get_portfolio_workflow_analysis(portfolio_id: str, workflow_id: str):
    """Retrieve individual workflow analysis overview for a workflow in a portfolio."""
    storage = get_storage()
    portfolio = storage.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio with ID '{portfolio_id}' not found or session has expired.",
        )

    res = storage.get(workflow_id)
    if res is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow with ID '{workflow_id}' not found or session has expired.",
        )
    return to_overview_dto(res)


@router.get("/{portfolio_id}/rationalisation", response_model=RationalisationAnalysisDTO)
def get_portfolio_rationalisation(portfolio_id: str, use_llm: bool = True):
    """Retrieve full ETL rationalisation analysis for a portfolio."""
    storage = get_storage()
    portfolio = storage.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio with ID '{portfolio_id}' not found or session has expired.",
        )

    # Collect successful workflow CanonicalAnalysisResults
    successful_results: dict[str, Any] = {}
    for wf in portfolio.workflows:
        if wf.status == "SUCCESS":
            res = storage.get(wf.workflow_id)
            if res:
                successful_results[wf.workflow_id] = res

    from awa.analysis.rationalisation_analyzer import build_rationalisation_analysis
    from awa.llm import get_default_generator

    generator = None
    if use_llm:
        try:
            gen = get_default_generator()
            if getattr(gen, "client", None) and getattr(gen.client, "is_available", False):
                generator = gen
            else:
                logger.info("[Rationalisation] LLM client unavailable or disabled — proceeding with deterministic baseline.")
        except Exception as e:
            logger.warning("[Rationalisation] Could not obtain LLM generator: %s — proceeding with deterministic baseline.", e)

    try:
        analysis = build_rationalisation_analysis(
            portfolio=portfolio,
            successful_results=successful_results,
            generator=generator,
            use_llm=bool(use_llm and generator is not None),
        )
    except Exception as e:
        logger.exception("[Rationalisation] Unexpected error during rationalisation: %s — falling back to deterministic baseline.", e)
        analysis = build_rationalisation_analysis(
            portfolio=portfolio,
            successful_results=successful_results,
            generator=None,
            use_llm=False,
        )

    return RationalisationAnalysisDTO(**analysis.to_dict())


@router.get("/{portfolio_id}/export/xlsx")
def export_portfolio_xlsx(portfolio_id: str, background_tasks: BackgroundTasks):
    """Generate and stream a production-grade ETL Portfolio Overview Excel workbook (.xlsx)."""
    storage = get_storage()
    portfolio = storage.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio with ID '{portfolio_id}' not found or session has expired.",
        )

    # Collect successful workflow CanonicalAnalysisResults
    successful_results: dict[str, Any] = {}
    for wf in portfolio.workflows:
        if wf.status == "SUCCESS":
            res = storage.get(wf.workflow_id)
            if res:
                successful_results[wf.workflow_id] = res

    # Deterministic rationalisation projection (0 download-time LLM calls)
    from awa.analysis.rationalisation_analyzer import build_rationalisation_analysis
    try:
        rationalisation = build_rationalisation_analysis(
            portfolio=portfolio,
            successful_results=successful_results,
            generator=None,
            use_llm=False,
        )
    except Exception as exc:
        logger.warning("[Portfolio XLSX] Could not build rationalisation: %s", exc)
        rationalisation = None

    # Safe temporary file lifecycle with BackgroundTasks cleanup
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tf:
        temp_path = Path(tf.name)

    from awa.generators.portfolio_xlsx_generator import generate_portfolio_excel
    generate_portfolio_excel(
        portfolio=portfolio,
        successful_results=successful_results,
        rationalisation=rationalisation,
        output_path=temp_path,
    )

    def _cleanup_temp_file(path: str):
        try:
            Path(path).unlink(missing_ok=True)
        except Exception as err:
            logger.warning("[Portfolio XLSX] Failed to remove temp file %s: %s", path, err)

    background_tasks.add_task(_cleanup_temp_file, str(temp_path))

    safe_name = re.sub(r"[^\w\-.]", "_", portfolio.portfolio_name or "ETL_Portfolio")
    filename = f"{safe_name}_Overview.xlsx"

    return FileResponse(
        path=temp_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


