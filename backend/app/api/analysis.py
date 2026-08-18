"""Analysis query endpoints — retrieves views over CanonicalAnalysisResult."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.app.models.schemas import (
    AnalysisOverviewDTO,
    DiagramDTO,
    PythonOutputDTO,
)
from backend.app.services.analyzer import (
    to_overview_dto,
    to_diagram_dto,
    to_python_dto,
)
from backend.app.services.storage import get_storage

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _get_result_or_404(analysis_id: str):
    storage = get_storage()
    result = storage.get(analysis_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis with ID '{analysis_id}' not found or session has expired.",
        )
    return result


@router.get("/{analysis_id}", response_model=AnalysisOverviewDTO)
def get_analysis(analysis_id: str):
    """Retrieve full analysis overview."""
    res = _get_result_or_404(analysis_id)
    return to_overview_dto(res)


@router.get("/{analysis_id}/overview", response_model=AnalysisOverviewDTO)
def get_analysis_overview(analysis_id: str):
    """Retrieve workflow overview metrics and metadata."""
    res = _get_result_or_404(analysis_id)
    return to_overview_dto(res)


@router.get("/{analysis_id}/diagram", response_model=DiagramDTO)
def get_analysis_diagram(analysis_id: str):
    """Retrieve SVG string, node details, and DAG layout."""
    res = _get_result_or_404(analysis_id)
    return to_diagram_dto(res)


@router.get("/{analysis_id}/json")
def get_analysis_json(analysis_id: str):
    """Retrieve the complete canonical workflow JSON representation."""
    res = _get_result_or_404(analysis_id)
    return JSONResponse(content=res.to_dict())


@router.get("/{analysis_id}/python", response_model=PythonOutputDTO)
def get_analysis_python(analysis_id: str):
    """Retrieve the generated Python/pandas pipeline and traceability map."""
    res = _get_result_or_404(analysis_id)
    return to_python_dto(res)


@router.get("/{analysis_id}/diagnostics")
def get_analysis_diagnostics(analysis_id: str):
    """Retrieve all diagnostic messages and support statistics."""
    res = _get_result_or_404(analysis_id)
    diags = [d.to_dict() for d in res.diagnostics]
    return {
        "analysis_id": analysis_id,
        "diagnostics": diags,
        "support_summary": res.metrics.support_summary,
        "total_diagnostics": len(diags),
    }
