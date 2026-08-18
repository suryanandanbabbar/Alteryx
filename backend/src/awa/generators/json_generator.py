"""JSON generator — serializes Workflow IR to workflow.json."""

from __future__ import annotations

import json
from pathlib import Path

from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult


def generate_json(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    output_path: Path,
) -> None:
    """Generate workflow.json from the Workflow IR.

    Contains:
    - Workflow metadata
    - Tools with configurations
    - Connections
    - Execution order (from topological sort)
    - Dependencies
    - Diagnostics
    - Analysis summary
    """
    # Collect all diagnostics from translations
    all_diagnostics = list(workflow.diagnostics)
    for tr in translations.values():
        all_diagnostics.extend(tr.diagnostics)

    # Build analysis summary
    support_counts: dict[str, int] = {}
    for tr in translations.values():
        level = tr.support_level.value
        support_counts[level] = support_counts.get(level, 0) + 1

    output = {
        "metadata": workflow.metadata.to_dict(),
        "tools": [
            workflow.tools[tid].to_dict()
            for tid in execution_order
            if tid in workflow.tools
        ],
        "connections": [c.to_dict() for c in workflow.connections],
        "execution_order": execution_order,
        "dependencies": [d.to_dict() for d in workflow.dependencies],
        "diagnostics": [d.to_dict() for d in all_diagnostics],
        "analysis": {
            "total_tools": len(workflow.tools),
            "support_summary": support_counts,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
