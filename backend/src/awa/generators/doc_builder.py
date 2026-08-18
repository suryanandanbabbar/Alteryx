"""Document model builder — transforms CanonicalAnalysisResult into DocumentModel.

Produces a format-independent representation of documentation content
that renderers (like docx_generator) consume without touching workflow internals.
"""

from __future__ import annotations

from backend.src.awa.model.workflow import Workflow
from backend.src.awa.model.translation import TranslationResult
from backend.src.awa.model.dag_layout import DagLayout
from backend.src.awa.model.doc_model import DocumentModel, NodeDocEntry, ExecutionStepDocEntry
from backend.src.awa.model.visual_category import get_visual_category
from backend.src.awa.graph.lineage import LineagePath


def build_document_model(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    dag_layout: DagLayout,
    lineage_paths: list[LineagePath],
) -> DocumentModel:
    """Build the canonical DocumentModel from workflow analysis data.

    Args:
        workflow: Canonical Workflow IR.
        execution_order: Tool IDs in topological order.
        translations: Tool translations keyed by tool_id.
        dag_layout: Computed DAG layout model.
        lineage_paths: Computed source-to-sink data lineage paths.

    Returns:
        Format-independent DocumentModel.
    """
    # 1. Metadata dict
    metadata: dict[str, str] = {
        "Name": workflow.metadata.name or "Untitled Workflow",
        "Version": workflow.metadata.version or "Unknown",
    }
    if workflow.metadata.author:
        metadata["Author"] = workflow.metadata.author
    if workflow.metadata.description:
        metadata["Description"] = workflow.metadata.description

    # 2. Metrics dict
    input_count = sum(
        1 for t in workflow.tools.values()
        if t.tool_type in ("DbFileInput", "InputData", "TextInput", "DynamicInput")
    )
    output_count = sum(
        1 for t in workflow.tools.values()
        if t.tool_type in ("DbFileOutput", "OutputData", "Browse")
    )
    metrics: dict[str, int] = {
        "Total Tools": len(workflow.tools),
        "Total Connections": len(workflow.connections),
        "Input Tools": input_count,
        "Output Tools": output_count,
    }

    # 3. Execution steps
    exec_steps: list[ExecutionStepDocEntry] = []
    for step_num, tool_id in enumerate(execution_order, start=1):
        tool = workflow.tools.get(tool_id)
        tool_type = tool.tool_type if tool else "Unknown"
        name = (tool.name if tool and tool.name else tool_type)
        vcat = get_visual_category(tool_type)
        exec_steps.append(
            ExecutionStepDocEntry(
                step_number=step_num,
                tool_id=tool_id,
                tool_type=tool_type,
                name=name,
                visual_category=vcat,
            )
        )

    # 4. Node documentation entries
    node_entries: list[NodeDocEntry] = []
    for tool_id in execution_order:
        tool = workflow.tools.get(tool_id)
        if not tool:
            continue
        tr = translations.get(tool_id)
        support_level = tr.support_level.value if tr else "unknown"
        description = tr.description if tr else ""
        input_vars = tr.input_variables if tr else []
        output_vars = tr.output_map if tr else {}
        diags = tr.diagnostics if tr else []

        node_entries.append(
            NodeDocEntry(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                name=tool.name or tool.tool_type,
                plugin=tool.plugin,
                support_level=support_level,
                annotation=tool.annotation,
                description=description,
                configuration=tool.configuration.parsed,
                input_variables=input_vars,
                output_variables=output_vars,
                diagnostics=diags,
            )
        )

    # 5. Python summary text
    supported_tools = sum(1 for tr in translations.values() if tr.support_level.value == "supported")
    total_tr = len(translations)
    python_summary = (
        f"Generated deterministic Python/pandas script with {supported_tools}/{total_tr} "
        f"tools fully supported."
    )

    # 6. All diagnostics (workflow-level + tool-level)
    all_diags = list(workflow.diagnostics)
    for tr in translations.values():
        all_diags.extend(tr.diagnostics)

    return DocumentModel(
        title=f"Alteryx Workflow Documentation: {workflow.metadata.name}",
        metadata=metadata,
        metrics=metrics,
        execution_order=exec_steps,
        dag_layout=dag_layout,
        nodes=node_entries,
        lineage_paths=lineage_paths,
        python_summary=python_summary,
        dependencies=workflow.dependencies,
        diagnostics=all_diags,
    )
