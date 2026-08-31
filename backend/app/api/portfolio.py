"""Portfolio endpoints — query and upload multi-workflow portfolios."""

from __future__ import annotations

import logging
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from awa.parser.format_handler import detect_format
from backend.app.config import settings
from backend.app.models.schemas import (
    AnalysisOverviewDTO,
    PortfolioOverviewDTO,
    PortfolioWorkflowSummaryDTO,
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
