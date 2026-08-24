"""Document model builder — transforms CanonicalAnalysisResult into DocumentModel.

Produces a format-independent representation of documentation content
that renderers (like docx_generator) consume without touching workflow internals.
"""

from __future__ import annotations

from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.dag_layout import DagLayout
from awa.model.doc_model import DocumentModel, NodeDocEntry, ExecutionStepDocEntry
from awa.model.visual_category import get_visual_category
from awa.graph.lineage import LineagePath
from awa.tools import get_tool_summary, humanize_tool_configuration


from awa.model.business_summary import WorkflowBusinessSummary


def build_document_model(
    workflow: Workflow,
    execution_order: list[int],
    translations: dict[int, TranslationResult],
    dag_layout: DagLayout,
    lineage_paths: list[LineagePath],
    business_summary: WorkflowBusinessSummary | None = None,
) -> DocumentModel:
    """Build the canonical DocumentModel from workflow analysis data.

    Args:
        workflow: Canonical Workflow IR.
        execution_order: Tool IDs in topological order.
        translations: Tool translations keyed by tool_id.
        dag_layout: Computed DAG layout model.
        lineage_paths: Computed source-to-sink data lineage paths.
        business_summary: Optional canonical business intelligence summary.

    Returns:
        Format-independent DocumentModel.
    """
    # 1. Metadata dict
    metadata: dict[str, str] = {
        "Workflow Name": workflow.metadata.name or "Untitled Workflow",
        "Alteryx Version": workflow.metadata.version or "2024.1",
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
        "Data Inputs": input_count,
        "Data Outputs": output_count,
    }

    from awa.llm import get_default_generator
    generator = get_default_generator()
    wf_key = workflow.metadata.name or "default_workflow"

    # 3. Execution steps
    exec_steps: list[ExecutionStepDocEntry] = []
    for step_num, tool_id in enumerate(execution_order, start=1):
        tool = workflow.tools.get(tool_id)
        tool_type = tool.tool_type if tool else "Unknown"
        name = (tool.name if tool and tool.name else tool_type)
        vcat = get_visual_category(tool_type)
        summary = (
            generator.generate_tool_summary(workflow, tool, workflow_id=wf_key).text
            if tool
            else get_tool_summary(tool_type)
        )
        exec_steps.append(
            ExecutionStepDocEntry(
                step_number=step_num,
                tool_id=tool_id,
                tool_type=tool_type,
                name=name,
                visual_category=vcat,
                summary=summary,
                container_id=tool.container_id if tool else None,
                container_name=tool.container_name if tool else None,
            )
        )

    # 4. Node documentation entries
    node_entries: list[NodeDocEntry] = []
    for tool_id in execution_order:
        tool = workflow.tools.get(tool_id)
        if not tool:
            continue
        tr = translations.get(tool_id)
        description = tr.description if tr else ""
        input_vars = tr.input_variables if tr else []
        output_vars = tr.output_map if tr else {}
        summary = generator.generate_tool_summary(workflow, tool, workflow_id=wf_key).text

        node_entries.append(
            NodeDocEntry(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                name=tool.name or tool.tool_type,
                plugin=tool.plugin,
                annotation=tool.annotation,
                description=description,
                summary=summary,
                configuration=humanize_tool_configuration(tool.tool_type, tool.configuration.parsed),
                input_variables=input_vars,
                output_variables=output_vars,
                container_id=tool.container_id,
                container_name=tool.container_name,
            )
        )

    # 5. Python summary text
    python_summary = (
        f"Automated deterministic Python/pandas translation pipeline covering "
        f"{len(workflow.tools)} workflow tools."
    )

    # 6. All diagnostics (preserved in internal model for technical consumers)
    all_diags = list(workflow.diagnostics)
    for tr in translations.values():
        all_diags.extend(tr.diagnostics)

    return DocumentModel(
        title=f"Workflow Analysis Report: {workflow.metadata.name or 'Alteryx Workflow'}",
        metadata=metadata,
        metrics=metrics,
        execution_order=exec_steps,
        dag_layout=dag_layout,
        nodes=node_entries,
        lineage_paths=lineage_paths,
        python_summary=python_summary,
        dependencies=workflow.dependencies,
        diagnostics=all_diags,
        business_summary=business_summary,
    )
