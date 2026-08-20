"""Workflow analyzer — orchestrates parsing, graph building, translation, and artifact generation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

from awa.model.workflow import Workflow
from awa.model.translation import TranslationResult
from awa.model.source_info import SourceInfo
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.python_trace import ToolExplanation
from awa.parser.xml_parser import parse_workflow
from awa.graph.builder import build_graph, execution_order, consumed_anchors, build_input_map
from awa.graph.lineage import compute_lineage_paths
from awa.graph.dag_layouter import compute_dag_layout
from awa.translators.registry import get_translator
from awa.tools.catalog import get_tool_catalog
import awa.translators  # noqa: F401
from awa.generators.json_generator import generate_json
from awa.generators.python_generator import generate_python, generate_python_code
from awa.generators.diagnostics_generator import generate_diagnostics
from awa.generators.svg_generator import generate_svg
from awa.generators.docx_generator import generate_docx
from awa.generators.doc_builder import build_document_model


@dataclass
class AnalysisResult:
    """Result of analyzing a workflow."""
    workflow: Workflow
    execution_order: list[int]
    translations: dict[int, TranslationResult]
    output_dir: Path


def analyze_canonical(
    workflow_path: str | Path,
    source_info: SourceInfo | None = None,
    analysis_id: str | None = None,
) -> CanonicalAnalysisResult:
    """Perform full canonical analysis of an Alteryx workflow.

    Args:
        workflow_path: Path to the workflow file (.yxmd, .yxwz, or .xml).
        source_info: Optional source metadata.
        analysis_id: Optional UUID string.

    Returns:
        CanonicalAnalysisResult representing the single source of truth.
    """
    path = Path(workflow_path)
    aid = analysis_id or str(uuid.uuid4())
    sinfo = source_info or SourceInfo(
        source_format="yxmd",
        original_filename=path.name,
    )
    catalog = get_tool_catalog()

    # 1. Parse into canonical IR
    workflow = parse_workflow(path)

    # 2. Build graph & topological order
    graph = build_graph(workflow)
    exec_order = execution_order(graph)
    consumed = consumed_anchors(workflow)
    input_map = build_input_map(workflow)

    # 3. Translate tools and collect explanations
    translations: dict[int, TranslationResult] = {}
    tool_explanations: dict[int, ToolExplanation] = {}

    for tool_id in exec_order:
        tool = workflow.tools[tool_id]
        translator = get_translator(tool)
        input_vars = input_map.get(tool_id, [])
        result = translator.translate(tool, input_vars, workflow)
        translations[tool_id] = result
        tool_explanations[tool_id] = translator.explain(tool, result)

    # 4. Compute lineage paths
    lineage_paths = compute_lineage_paths(workflow, graph)

    # 5. Compute DAG layout
    dag_layout = compute_dag_layout(graph, workflow, exec_order)

    # 6. Generate Python code & line-level trace map
    code, trace_map, required_libs = generate_python_code(
        workflow, exec_order, translations, consumed
    )

    # 7. Collect all diagnostics
    all_diags = list(workflow.diagnostics)
    for tr in translations.values():
        all_diags.extend(tr.diagnostics)

    # 8. Compute workflow metrics using Tool Registry catalog
    input_node_ids = []
    output_node_ids = []
    for tid in exec_order:
        if tid in workflow.tools:
            tool = workflow.tools[tid]
            tdef = catalog.resolve(tool.plugin or tool.tool_type)
            if not tdef.input_anchors or tool.tool_type in ("DbFileInput", "InputData", "TextInput", "DynamicInput", "Directory", "DateTimeNow"):
                input_node_ids.append(tid)
            if not tdef.output_anchors or tool.tool_type in ("DbFileOutput", "OutputData", "Browse", "BrowseV2", "Render"):
                output_node_ids.append(tid)

    support_counts: dict[str, int] = {}
    for tr in translations.values():
        lvl = tr.support_level.value
        support_counts[lvl] = support_counts.get(lvl, 0) + 1

    metrics = WorkflowMetrics(
        total_nodes=len(workflow.tools),
        total_connections=len(workflow.connections),
        input_count=len(input_node_ids),
        output_count=len(output_node_ids),
        container_count=len(workflow.containers),
        annotation_count=len(workflow.textboxes),
        input_node_ids=input_node_ids,
        output_node_ids=output_node_ids,
        support_summary=support_counts,
    )

    return CanonicalAnalysisResult(
        analysis_id=aid,
        source=sinfo,
        workflow=workflow,
        graph=graph,
        execution_order=exec_order,
        translations=translations,
        consumed_anchors=consumed,
        lineage_paths=lineage_paths,
        metrics=metrics,
        dag_layout=dag_layout,
        python_trace=trace_map,
        tool_explanations=tool_explanations,
        required_libraries=required_libs,
        diagnostics=all_diags,
    )


def analyze_workflow(
    workflow_path: str | Path,
    output_dir: str | Path | None = None,
) -> AnalysisResult:
    """Analyze an Alteryx workflow and generate export artifacts.

    Args:
        workflow_path: Path to the workflow file.
        output_dir: Directory for output artifacts.

    Returns:
        AnalysisResult with workflow, translations, and output location.
    """
    workflow_path = Path(workflow_path)
    canonical = analyze_canonical(workflow_path)
    workflow = canonical.workflow
    exec_order = canonical.execution_order
    translations = canonical.translations
    consumed = canonical.consumed_anchors
    lineage_paths = canonical.lineage_paths

    if output_dir is None:
        output_dir = workflow_path.parent / f"{workflow.metadata.name}_analysis"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. workflow.json
    generate_json(
        workflow, exec_order, translations,
        output_dir / "workflow.json",
    )

    # 2. workflow.py
    generate_python(
        workflow, exec_order, translations, consumed,
        output_dir / "workflow.py",
    )

    # 3. diagnostics.json
    generate_diagnostics(
        workflow, translations,
        output_dir / "diagnostics.json",
    )

    # 4. workflow.svg
    svg_str = generate_svg(canonical.dag_layout)
    with open(output_dir / "workflow.svg", "w", encoding="utf-8") as f:
        f.write(svg_str)

    # 5. workflow.docx
    doc_model = build_document_model(
        workflow, exec_order, translations, canonical.dag_layout, lineage_paths
    )
    generate_docx(doc_model, output_dir / "workflow.docx", svg_content=svg_str)

    return AnalysisResult(
        workflow=workflow,
        execution_order=exec_order,
        translations=translations,
        output_dir=output_dir,
    )
