"""Diagnostics generator — produces diagnostics.json."""

from __future__ import annotations

import json
from pathlib import Path

from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult


def generate_diagnostics(
    workflow: Workflow,
    translations: dict[int, TranslationResult],
    output_path: Path,
) -> None:
    """Generate diagnostics.json with all diagnostic messages."""
    all_diagnostics = []

    # Workflow-level diagnostics
    for diag in workflow.diagnostics:
        all_diagnostics.append(diag.to_dict())

    # Tool-level diagnostics from translations
    for tr in sorted(translations.values(), key=lambda t: t.tool_id):
        for diag in tr.diagnostics:
            all_diagnostics.append(diag.to_dict())

    # Summary
    summary: dict[str, int] = {}
    for diag in all_diagnostics:
        level = diag.get("level", "unknown")
        summary[level] = summary.get(level, 0) + 1

    # Support level summary
    support_summary: dict[str, int] = {}
    for tr in translations.values():
        level = tr.support_level.value
        support_summary[level] = support_summary.get(level, 0) + 1

    output = {
        "diagnostics": all_diagnostics,
        "summary": {
            "total_diagnostics": len(all_diagnostics),
            "by_level": summary,
            "tool_support": support_summary,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
