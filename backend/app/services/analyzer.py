"""Analyzer service — bridges format upload, analysis engine, and DTO mapping."""

from __future__ import annotations

import tempfile
from pathlib import Path

from awa.parser.format_handler import handle_upload
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.visual_category import get_visual_category
from awa.tools import get_tool_summary, humanize_tool_configuration

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
    WorkflowBusinessSummaryDTO,
    BusinessInputDTO,
    BusinessOutputDTO,
    BusinessStageDTO,
    BusinessTransformationDTO,
    BusinessRuleDTO,
    BusinessLineageDTO,
    BusinessAssessmentDTO,
    PythonOutputDTO,
    PythonTraceDTO,
)
from awa.generators.svg_generator import generate_svg


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
        terminal_node_count=res.metrics.terminal_node_count,
        terminal_node_ids=res.metrics.terminal_node_ids,
        business_output_count=res.metrics.business_output_count,
        business_output_node_ids=res.metrics.business_output_node_ids,
        container_count=res.metrics.container_count,
        annotation_count=res.metrics.annotation_count,
        input_node_ids=res.metrics.input_node_ids,
        output_node_ids=res.metrics.output_node_ids,
        support_summary=res.metrics.support_summary,
    )

    exec_steps: list[ExecutionStepDTO] = []
    for idx, tid in enumerate(res.execution_order, start=1):
        tool = res.workflow.tools.get(tid)
        ttype = tool.tool_type if tool else "Unknown"
        name = (tool.name if tool and tool.name else ttype)
        summary = get_tool_summary(tool.plugin or ttype) if tool else get_tool_summary(ttype)
        container_id = tool.container_id if tool else None
        container_name = tool.container_name if tool else None
        exec_steps.append(
            ExecutionStepDTO(
                step_number=idx,
                tool_id=tid,
                tool_type=ttype,
                name=name,
                visual_category=get_visual_category(ttype),
                summary=summary,
                container_id=container_id,
                container_name=container_name,
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

    # Map Business Summary
    bs_dto = None
    if res.business_summary:
        bs = res.business_summary
        bs_dto = WorkflowBusinessSummaryDTO(
            business_purpose=bs.business_purpose,
            one_line_purpose=bs.one_line_purpose,
            why_it_matters=bs.why_it_matters,
            source_inputs=[
                BusinessInputDTO(
                    tool_id=inp.tool_id,
                    name=inp.name,
                    raw_source=inp.raw_source,
                    source_type=inp.source_type,
                    sheet_or_table=inp.sheet_or_table,
                    container_name=inp.container_name,
                    business_role=inp.business_role,
                    description=inp.description,
                )
                for inp in bs.source_inputs
            ],
            processing_stages=[
                BusinessStageDTO(
                    stage_number=stg.stage_number,
                    name=stg.name,
                    short_title=stg.short_title,
                    summary=stg.summary,
                    description=stg.description,
                    business_purpose=stg.business_purpose,
                    major_transformation=stg.major_transformation,
                    tool_ids=stg.tool_ids,
                    input_ids=stg.input_ids,
                    output_ids=stg.output_ids,
                    tool_count=stg.tool_count,
                    container_name=stg.container_name,
                    annotations=stg.annotations,
                    transformations=stg.transformations,
                )
                for stg in bs.processing_stages
            ],
            transformations=[
                BusinessTransformationDTO(
                    category=tr.category,
                    description=tr.description,
                    affected_fields=tr.affected_fields,
                    tool_ids=tr.tool_ids,
                )
                for tr in bs.transformations
            ],
            business_rules=[
                BusinessRuleDTO(
                    rule_name=br.rule_name,
                    category=br.category,
                    description=br.description,
                    tool_ids=br.tool_ids,
                    evidence=br.evidence,
                )
                for br in bs.business_rules
            ],
            lineage=[
                BusinessLineageDTO(
                    source_name=lin.source_name,
                    transformation=lin.transformation,
                    target_name=lin.target_name,
                    intermediate_stages=lin.intermediate_stages,
                    transformation_summary=lin.transformation_summary,
                    source_tool_id=lin.source_tool_id,
                    target_tool_id=lin.target_tool_id,
                )
                for lin in bs.lineage
            ],
            business_outputs=[
                BusinessOutputDTO(
                    tool_id=out.tool_id,
                    name=out.name,
                    raw_destination=out.raw_destination,
                    destination_type=out.destination_type,
                    sheet_or_table=out.sheet_or_table,
                    business_meaning=out.business_meaning,
                    likely_use=out.likely_use,
                    business_purpose=out.business_purpose,
                    container_name=out.container_name,
                    upstream_sources=out.upstream_sources,
                )
                for out in bs.business_outputs
            ],
            assessment=BusinessAssessmentDTO(
                complexity=bs.assessment.complexity,
                complexity_reason=bs.assessment.complexity_reason,
                complexity_factors=bs.assessment.complexity_factors,
                platform=bs.assessment.platform,
                business_owner=bs.assessment.business_owner,
                schedule=bs.assessment.schedule,
                criticality=bs.assessment.criticality,
                documentation_quality=bs.assessment.documentation_quality,
                assessment_status=bs.assessment.assessment_status,
                key_observations=bs.assessment.key_observations,
                key_activities=bs.assessment.key_activities,
                key_findings=bs.assessment.key_findings,
                role_and_value=bs.assessment.role_and_value,
                assessment_gaps=bs.assessment.assessment_gaps,
                preliminary_disposition=bs.assessment.preliminary_disposition,
                disposition_rationale=bs.assessment.disposition_rationale,
                validation_checklist=bs.assessment.validation_checklist,
                why_it_matters=bs.assessment.why_it_matters,
            ) if bs.assessment else BusinessAssessmentDTO(),
            process_overview=bs.process_overview,
            information_flow=bs.information_flow,
            overall_interpretation=bs.overall_interpretation,
            confidence_level=bs.confidence_level,
        )

    return AnalysisOverviewDTO(
        analysis_id=res.analysis_id,
        source=source_dto,
        metadata=meta_dto,
        metrics=metrics_dto,
        execution_order=exec_steps,
        connections=conns_dto,
        diagnostics=diags_dto,
        business_summary=bs_dto,
    )


def to_diagram_dto(res: CanonicalAnalysisResult) -> DiagramDTO:
    """Convert CanonicalAnalysisResult to DiagramDTO."""
    svg_str = generate_svg(res.dag_layout)

    nodes_dto: list[NodeDTO] = []
    from awa.tools.catalog import get_tool_catalog
    catalog = get_tool_catalog()

    for tid in res.execution_order:
        tool = res.workflow.tools.get(tid)
        if not tool:
            continue
        tr = res.translations.get(tid)
        support = tr.support_level.value if tr else "unknown"
        summary = get_tool_summary(tool.plugin or tool.tool_type)
        tool_def = catalog.get(tool.plugin or tool.tool_type)
        xml_tool_name = tool_def.xml_name if tool_def else (tool.plugin or "")

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
                configuration=humanize_tool_configuration(tool.tool_type, tool.configuration.parsed),
                support_level=support,
                summary=summary,
                annotation=tool.annotation,
                output_fields=fields_dto,
                engine_settings=tool.engine_settings,
                visual_category=get_visual_category(tool.tool_type),
                container_id=tool.container_id,
                container_name=tool.container_name,
                raw_node_xml=tool.raw_node_xml,
                xml_tool_name=xml_tool_name,
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

    metrics_dto = WorkflowMetricsDTO(
        total_nodes=res.metrics.total_nodes,
        total_connections=res.metrics.total_connections,
        input_count=res.metrics.input_count,
        output_count=res.metrics.output_count,
        terminal_node_count=res.metrics.terminal_node_count,
        terminal_node_ids=res.metrics.terminal_node_ids,
        business_output_count=res.metrics.business_output_count,
        business_output_node_ids=res.metrics.business_output_node_ids,
        container_count=res.metrics.container_count,
        annotation_count=res.metrics.annotation_count,
        input_node_ids=res.metrics.input_node_ids,
        output_node_ids=res.metrics.output_node_ids,
        support_summary=res.metrics.support_summary,
    )

    return DiagramDTO(
        svg=svg_str,
        nodes=nodes_dto,
        dag_layout=layout_dto,
        connections=conns_dto,
        diagnostics=diags_dto,
        metrics=metrics_dto,
    )


def to_python_dto(res: CanonicalAnalysisResult) -> PythonOutputDTO:
    """Convert CanonicalAnalysisResult to PythonOutputDTO."""
    from awa.generators.python_generator import generate_python_code

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
