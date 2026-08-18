"""Workflow upload and analysis endpoint."""

from __future__ import annotations

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status

from awa.parser.format_handler import FormatValidationError
from backend.app.config import settings
from backend.app.models.schemas import AnalysisOverviewDTO
from backend.app.services.analyzer import process_uploaded_workflow, to_overview_dto
from backend.app.services.storage import get_storage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=AnalysisOverviewDTO)
async def upload_workflow(file: UploadFile = File(...)):
    """Upload an Alteryx workflow file (.yxmd, .yxwz, or .xml) and run deterministic analysis.

    Returns the canonical workflow overview and analysis_id for subsequent requests.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FILENAME_MISSING", "error": "FILENAME_MISSING", "message": "Filename is missing from upload."},
        )

    # Read uploaded bytes with size limit guard
    chunk_size = 1024 * 1024  # 1 MB chunk
    content = bytearray()
    max_bytes = settings.max_upload_bytes

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "error": "FILE_TOO_LARGE",
                    "message": f"Uploaded file exceeds maximum allowed size of {max_bytes} bytes.",
                },
            )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_FILE", "error": "EMPTY_FILE", "message": "Uploaded file is empty."},
        )

    try:
        # Process and analyze
        canonical_result = process_uploaded_workflow(file.filename, bytes(content))

        # Store in storage service
        storage = get_storage()
        storage.save(canonical_result)

        logger.info(
            "Successfully analyzed workflow '%s' (analysis_id: %s, nodes: %d)",
            file.filename,
            canonical_result.analysis_id,
            len(canonical_result.workflow.tools),
        )

        return to_overview_dto(canonical_result)

    except HTTPException:
        raise
    except FormatValidationError as e:
        logger.warning("Format validation failed for '%s': %s (%s)", file.filename, e.message, e.code)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": e.code, "error": e.code, "message": e.message},
        )
    except Exception:
        logger.exception("Unexpected error during analysis of '%s'", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ANALYSIS_FAILED",
                "error": "ANALYSIS_FAILED",
                "message": "An unexpected error occurred during workflow analysis.",
            },
        )
