"""Workflow upload and analysis endpoint."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException

from awa.parser.format_handler import FormatValidationError
from backend.app.models.schemas import AnalysisOverviewDTO
from backend.app.services.analyzer import process_uploaded_workflow, to_overview_dto
from backend.app.services.storage import get_storage

router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=AnalysisOverviewDTO)
async def upload_workflow(file: UploadFile = File(...)):
    """Upload an Alteryx workflow file (.yxmd, .yxwz, or .xml) and run deterministic analysis.

    Returns the canonical workflow overview and analysis_id for subsequent requests.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload.")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Process and analyze
        canonical_result = process_uploaded_workflow(file.filename, content)

        # Store in storage service
        storage = get_storage()
        storage.save(canonical_result)

        # Return overview DTO
        return to_overview_dto(canonical_result)

    except HTTPException:
        raise
    except FormatValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during workflow analysis: {str(e)}",
        )
