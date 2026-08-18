"""Markdown documentation generator — produces workflow.md."""

from __future__ import annotations

from pathlib import Path

from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.graph.lineage import LineagePath


def generate_markdown(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    lineage_paths: list[LineagePath],
    output_path: Path,
) -> None:
    """Generate workflow.md documentation."""
    lines: list[str] = []

    # Title
    lines.append(f"# Workflow: {workflow.metadata.name}")
    lines.append("")

    # Overview
    lines.append("## Overview")
    lines.append("")
    lines.append(f"This document describes the Alteryx workflow **{workflow.metadata.name}** ")
    lines.append(f"based on deterministic static analysis of the `.yxmd` file.")
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"| Property | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Name** | {workflow.metadata.name} |")
    lines.append(f"| **Version** | {workflow.metadata.version} |")
    if workflow.metadata.author:
        lines.append(f"| **Author** | {workflow.metadata.author} |")
    if workflow.metadata.description:
        lines.append(f"| **Description** | {workflow.metadata.description} |")
    lines.append(f"| **Total Tools** | {len(workflow.tools)} |")
    lines.append(f"| **Connections** | {len(workflow.connections)} |")
    lines.append("")

    # Data Sources
    source_tools = [
        workflow.tools[tid] for tid in execution_order
        if tid in workflow.tools
        and workflow.tools[tid].tool_type in ("DbFileInput", "InputData", "TextInput")
    ]
    if source_tools:
        lines.append("## Data Sources")
        lines.append("")
        for t in source_tools:
            file_path = t.configuration.parsed.get("file_path", "(unknown)")
            lines.append(f"- **Tool #{t.tool_id}** ({t.name or t.tool_type}): `{file_path}`")
        lines.append("")

    # Step-by-Step
    lines.append("## Step-by-Step Workflow")
    lines.append("")
    for step_num, tid in enumerate(execution_order, 1):
        tool = workflow.tools.get(tid)
        tr = translations.get(tid)
        if tool is None:
            continue

        lines.append(f"### Step {step_num}: {tool.name or tool.tool_type} (Tool #{tool.tool_id})")
        lines.append("")
        lines.append(f"| Property | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| **Type** | {tool.tool_type} |")
        lines.append(f"| **Plugin** | `{tool.plugin}` |")
        if tr:
            lines.append(f"| **Support** | {tr.support_level.value} |")
            if tr.description:
                lines.append(f"| **Description** | {tr.description} |")
            if tr.input_variables:
                lines.append(f"| **Inputs** | {', '.join(f'`{v}`' for v in tr.input_variables)} |")
            if tr.output_map:
                outputs = ', '.join(f'{k}: `{v}`' for k, v in tr.output_map.items())
                lines.append(f"| **Outputs** | {outputs} |")
        lines.append("")

        # Show diagnostics
        if tr and tr.diagnostics:
            for diag in tr.diagnostics:
                lines.append(f"> **{diag.level.value.upper()}**: {diag.message}")
            lines.append("")

    # Data Lineage
    if lineage_paths:
        lines.append("## Data Lineage")
        lines.append("")
        for i, lp in enumerate(lineage_paths, 1):
            path_str = " → ".join(
                f"{name} (#{tid})"
                for tid, name in zip(lp.tool_ids, lp.tool_names)
            )
            lines.append(f"{i}. {path_str}")
        lines.append("")

    # Tool Inventory
    lines.append("## Tool Inventory")
    lines.append("")
    lines.append("| Tool ID | Type | Name | Support |")
    lines.append("|---|---|---|---|")
    for tid in execution_order:
        tool = workflow.tools.get(tid)
        tr = translations.get(tid)
        if tool:
            support = tr.support_level.value if tr else "unknown"
            lines.append(
                f"| {tool.tool_id} | {tool.tool_type} | "
                f"{tool.name or '—'} | {support} |"
            )
    lines.append("")

    # Dependencies
    if workflow.dependencies:
        lines.append("## Dependencies")
        lines.append("")
        for dep in workflow.dependencies:
            lines.append(f"- **{dep.dep_type}**: `{dep.reference}` (Tool #{dep.tool_id})")
        lines.append("")

    # Diagnostics Summary
    all_diags = list(workflow.diagnostics)
    for tr in translations.values():
        all_diags.extend(tr.diagnostics)

    if all_diags:
        lines.append("## Diagnostics")
        lines.append("")
        for diag in all_diags:
            tool_ref = f" (Tool #{diag.tool_id})" if diag.tool_id else ""
            lines.append(f"- **{diag.level.value.upper()}**{tool_ref}: {diag.message}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
