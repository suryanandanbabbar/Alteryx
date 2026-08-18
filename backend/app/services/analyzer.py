"""Analyzer service — bridges format upload, analysis engine, and DTO mapping."""

from __future__ import annotations

import tempfile
from pathlib import Path

from backend.src.awa.parser.format_handler import handle_upload
from backend.src.awa.analysis.workflow_analyzer import analyze_canonical
from backend.src.awa.model.analysis_result import CanonicalAnalysisResult
from backend.src.awa.model.visual_category import get_visual_category

from backend.app.models.schemas import (
    AnalysisOverviewDTO,
    SourceInfoDTO,
    PackageMetadataDTO,
    WorkflowMetadataDTO,
    WorkflowMetricsDTO,
    ExecutionStepDTO,
    ConnectionDTO,
    DiagnosticDTO,
    NodeDTO,
    FieldDTO,
    PositionDTO,
    DiagramDTO,
    DagLayoutDTO,
    DagNodeLayoutDTO,
    DagEdgeLayoutDTO,
    PythonOutputDTO,
    PythonTraceDTO,
)
from backend.src.awa.generators.svg_generator import generate_svg


def process_uploaded_workflow(filename: str, content: bytes) -> CanonicalAnalysisResult:
    """Validate, extract, and analyze an uploaded workflow file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        extracted_path, source_info = handle_upload(filename, content, temp_path)
        canonical_result = analyze_canonical(extracted_path, source_info=source_info)
        return canonical_result


def to_overview_dto(res: CanonicalAnalysisResult) -> AnalysisOverviewDTO:
    """Convert CanonicalAnalysisResult to AnalysisOverviewDTO."""
    pkg_dto = None
    if res.source.package_metadata:
        pkg_dto = PackageMetadataDTO(
            primary_workflow=res.source.package_metadata.primary_workflow,
            contained_files=res.source.package_metadata.contained_files,
            total_size_bytes=res.source.package_metadata.total_size_bytes,
        )

    source_dto = SourceInfoDTO(
        source_format=res.source.source_format,
        original_filename=res.source.original_filename,
        package_metadata=pkg_dto,
    )

    meta_dto = WorkflowMetadataDTO(
        name=res.workflow.metadata.name,
        version=res.workflow.metadata.version,
        author=res.workflow.metadata.author,
        description=res.workflow.metadata.description,
    )

    metrics_dto = WorkflowMetricsDTO(
        total_nodes=res.metrics.total_nodes,
        total_connections=res.metrics.total_connections,
        input_count=res.metrics.input_count,
        output_count=res.metrics.output_count,
        input_node_ids=res.metrics.input_node_ids,
        output_node_ids=res.metrics.output_node_ids,
        support_summary=res.metrics.support_summary,
    )

    exec_steps: list[ExecutionStepDTO] = []
    for idx, tid in enumerate(res.execution_order, start=1):
        tool = res.workflow.tools.get(tid)
        ttype = tool.tool_type if tool else "Unknown"
        name = (tool.name if tool and tool.name else ttype)
        exec_steps.append(
            ExecutionStepDTO(
                step_number=idx,
                tool_id=tid,
                tool_type=ttype,
                name=name,
                visual_category=get_visual_category(ttype),
            )
        )

    conns_dto = [
        ConnectionDTO(
            origin_tool_id=c.origin_tool_id,
            origin_anchor=c.origin_anchor,
            destination_tool_id=c.destination_tool_id,
            destination_anchor=c.destination_anchor,
        )
        for c in res.workflow.connections
    ]

    diags_dto = [
        DiagnosticDTO(
            level=d.level.value,
            category=d.category,
            tool_id=d.tool_id,
            tool_type=d.tool_type,
            message=d.message,
            detail=d.detail,
        )
        for d in res.diagnostics
    ]

    return AnalysisOverviewDTO(
        analysis_id=res.analysis_id,
        source=source_dto,
        metadata=meta_dto,
        metrics=metrics_dto,
        execution_order=exec_steps,
        connections=conns_dto,
        diagnostics=diags_dto,
    )


def to_diagram_dto(res: CanonicalAnalysisResult) -> DiagramDTO:
    """Convert CanonicalAnalysisResult to DiagramDTO."""
    svg_str = generate_svg(res.dag_layout)

    nodes_dto: list[NodeDTO] = []
    for tid in res.execution_order:
        tool = res.workflow.tools.get(tid)
        if not tool:
            continue
        tr = res.translations.get(tid)
        support = tr.support_level.value if tr else "unknown"

        pos_dto = PositionDTO(x=tool.position.x, y=tool.position.y) if tool.position else None
        fields_dto = [
            FieldDTO(name=f.name, type=f.type, size=f.size, scale=f.scale)
            for f in tool.output_fields
        ]

        nodes_dto.append(
            NodeDTO(
                tool_id=tool.tool_id,
                tool_type=tool.tool_type,
                name=tool.name or tool.tool_type,
                plugin=tool.plugin,
                position=pos_dto,
                configuration=tool.configuration.parsed,
                support_level=support,
                annotation=tool.annotation,
                output_fields=fields_dto,
                engine_settings=tool.engine_settings,
                visual_category=get_visual_category(tool.tool_type),
            )
        )

    layout_nodes = [
        DagNodeLayoutDTO(
            tool_id=n.tool_id,
            x=n.x,
            y=n.y,
            width=n.width,
            height=n.height,
            label=n.label,
            tool_type=n.tool_type,
            execution_index=n.execution_index,
            visual_category=n.visual_category,
        )
        for n in res.dag_layout.nodes
    ]

    layout_edges = [
        DagEdgeLayoutDTO(
            source_id=e.source_id,
            target_id=e.target_id,
            source_anchor=e.source_anchor,
            target_anchor=e.target_anchor,
            path_points=[{"x": p[0], "y": p[1]} for p in e.path_points],
        )
        for e in res.dag_layout.edges
    ]

    layout_dto = DagLayoutDTO(
        nodes=layout_nodes,
        edges=layout_edges,
        width=res.dag_layout.width,
        height=res.dag_layout.height,
        title=res.dag_layout.title,
    )

    return DiagramDTO(
        svg=svg_str,
        nodes=nodes_dto,
        dag_layout=layout_dto,
    )


def to_python_dto(res: CanonicalAnalysisResult) -> PythonOutputDTO:
    """Convert CanonicalAnalysisResult to PythonOutputDTO."""
    from backend.src.awa.generators.python_generator import generate_python_code

    code, trace_map, req_libs = generate_python_code(
        res.workflow, res.execution_order, res.translations, res.consumed_anchors
    )

    trace_dtos: list[PythonTraceDTO] = []
    for entry in trace_map.entries:
        exp = res.tool_explanations.get(entry.tool_id)
        reason = exp.why_selected if exp else entry.reason
        desc = exp.what_alteryx_does if exp else entry.description
        op = exp.what_pandas_does if exp else entry.pandas_op

        trace_dtos.append(
            PythonTraceDTO(
                tool_id=entry.tool_id,
                tool_type=entry.tool_type,
                tool_name=entry.tool_name,
                start_line=entry.start_line,
                end_line=entry.end_line,
                description=desc,
                pandas_op=op,
                reason=reason,
                libraries=entry.libraries,
            )
        )

    return PythonOutputDTO(
        code=code,
        required_libraries=req_libs,
        trace_map=trace_dtos,
        total_lines=trace_map.total_lines,
    )
