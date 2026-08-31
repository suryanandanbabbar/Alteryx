"""Portfolio service — handles multi-file discovery, individual workflow analysis, and portfolio orchestration."""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path
from typing import Any

from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.portfolio import PortfolioAnalysis
from awa.analysis.portfolio_analyzer import build_portfolio_analysis, enrich_portfolio_with_llm
from backend.app.services.analyzer import process_uploaded_workflow
from backend.app.services.storage import get_storage

logger = logging.getLogger(__name__)

SUPPORTED_WORKFLOW_EXTENSIONS = (".yxmd", ".yxwz", ".xml")


def extract_workflows_from_zip(
    zip_bytes: bytes,
    base_prefix: str = "",
) -> list[tuple[str, str, bytes]]:
    """Extract all valid workflow files (.yxmd, .yxwz, .xml) recursively from a ZIP archive.

    Silently ignores non-workflow files (.txt, .png, __MACOSX, etc.).
    Preserves relative paths within the archive.
    """
    discovered: list[tuple[str, str, bytes]] = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for zip_info in zf.infolist():
                # Skip directories and macOS resource forks
                if zip_info.is_dir() or "__MACOSX" in zip_info.filename or zip_info.filename.startswith("."):
                    continue

                filename = Path(zip_info.filename).name
                if filename.startswith("."):
                    continue

                ext = Path(filename).suffix.lower()
                if ext in SUPPORTED_WORKFLOW_EXTENSIONS:
                    try:
                        content = zf.read(zip_info)
                        if content:
                            prefix_clean = base_prefix.strip("./") if base_prefix else ""
                            rel_path = f"{prefix_clean}/{zip_info.filename}" if prefix_clean else zip_info.filename
                            discovered.append((filename, rel_path, content))
                    except Exception as e:
                        logger.warning("Failed to extract %s from zip: %s", zip_info.filename, e)
    except Exception as e:
        logger.warning("Could not read zip archive: %s", e)

    return discovered


def process_portfolio_uploads(
    uploaded_files: list[tuple[str, str, bytes]],
    portfolio_name: str = "ETL Portfolio",
) -> PortfolioAnalysis:
    """Process multiple discovered workflows through the canonical analysis pipeline.

    Enforces:
    - Reuse of canonical analysis pipeline for each YXMD
    - Storing each CanonicalAnalysisResult in storage service so individual views work natively
    - Partial failure resilience (failed workflows recorded with error message)
    - Deterministic portfolio evidence aggregation
    - LLM rationalisation qualification with safe deterministic fallback
    """
    storage = get_storage()
    raw_results: list[tuple[str, str, CanonicalAnalysisResult | Exception]] = []

    for filename, rel_path, content in uploaded_files:
        try:
            logger.info("Analyzing portfolio workflow: %s (%s)", filename, rel_path)
            canonical_res = process_uploaded_workflow(filename, content)
            # Store in global storage so all individual workflow routes/downloads work immediately
            storage.save(canonical_res)
            raw_results.append((filename, rel_path, canonical_res))
        except Exception as exc:
            logger.warning("Analysis failed for portfolio workflow '%s': %s", filename, exc)
            raw_results.append((filename, rel_path, exc))

    # 1. Build deterministic portfolio analysis
    portfolio = build_portfolio_analysis(raw_results, portfolio_name=portfolio_name)

    # 2. Enrich with portfolio LLM qualification (preserves deterministic baseline on failure)
    enriched_portfolio = enrich_portfolio_with_llm(portfolio)

    # 3. Store portfolio in storage service
    storage.save_portfolio(enriched_portfolio)

    logger.info(
        "Successfully created portfolio '%s' (ID: %s, Total: %d, Success: %d, Failed: %d)",
        enriched_portfolio.portfolio_name,
        enriched_portfolio.portfolio_id,
        enriched_portfolio.metrics.total_workflows,
        enriched_portfolio.metrics.successful_workflows,
        enriched_portfolio.metrics.failed_workflows,
    )

    return enriched_portfolio
