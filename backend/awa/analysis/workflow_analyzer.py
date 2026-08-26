"""Workflow analyzer — orchestrates parsing, graph building, translation, and artifact generation."""

from __future__ import annotations

import uuid
import re
import networkx as nx
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
from awa.generators.sttm_generator import generate_sttm_excel
from awa.generators.tool_specifications_generator import generate_tool_specifications_excel
from awa.model.tool_specifications import build_tool_specifications_document
from awa.analysis.business_intelligence import generate_business_summary
from awa.analysis.sttm_extractor import extract_sttm
from awa.llm.generator import get_default_generator


@dataclass
class AnalysisResult:
    """Result of analyzing a workflow."""
    workflow: Workflow
    execution_order: list[int]
    translations: dict[int, TranslationResult]
    output_dir: Path


def _extract_referenced_fields(expression: str) -> list[str]:
    """Extract column names enclosed in brackets or matched from an expression."""
    if not expression:
        return []
    bracketed = re.findall(r"\[([^\]]+)\]", expression)
    if bracketed:
        return list(dict.fromkeys(bracketed))
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", expression)
    keywords = {
        "if", "then", "else", "elseif", "endif", "isnull", "tonumber", "tostring",
        "datetimeadd", "datetimediff", "datetimetoday", "datetimeformat", "datetimenow",
        "and", "or", "not", "true", "false", "null", "days", "months", "years",
        "min", "max", "sum", "avg", "abs", "round", "trim", "left", "right", "length"
    }
    return [t for t in dict.fromkeys(tokens) if t.lower() not in keywords]


def discover_source_fields(workflow: Workflow, graph: nx.DiGraph) -> dict[int, list[str]]:
    """Identify initial intrinsic fields provided by each input dataset via generic DAG analysis."""
    input_tids = [
        tid for tid, t in workflow.tools.items()
        if t.tool_type in ("DbFileInput", "InputData", "TextInput", "Directory", "DynamicInput") or graph.in_degree(tid) == 0
    ]

    input_fields: dict[int, list[str]] = {tid: [] for tid in input_tids}

    has_explicit_schema = set()

    # 1. Level 1: Explicit XML RecordInfo or TextInput fields
    for tid in input_tids:
        tool = workflow.tools[tid]
        cfg = tool.configuration.parsed or {}
        xml_f = [f.name for f in tool.output_fields if f.name]
        if xml_f:
            input_fields[tid].extend(xml_f)
            has_explicit_schema.add(tid)
        elif "fields" in cfg:
            input_fields[tid].extend(cfg["fields"])
            has_explicit_schema.add(tid)

    # 2. Level 2: Subgraph analysis along isolated branch prior to joining
    for tid in input_tids:
        if tid in has_explicit_schema:
            continue
        visited = set()
        queue = [tid]
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            tool = workflow.tools.get(curr)
            if not tool:
                continue
            cfg = tool.configuration.parsed or {}

            if "select_fields" in cfg:
                for sf in cfg["select_fields"]:
                    f = sf.get("field")
                    if f and f != "*Unknown" and not f.startswith("Right_"):
                        input_fields[tid].append(f)

            if "formula_fields" in cfg:
                for ff in cfg["formula_fields"]:
                    input_fields[tid].extend(_extract_referenced_fields(ff.get("expression", "")))

            if "summarize_fields" in cfg:
                for sf in cfg["summarize_fields"]:
                    if sf.get("field"):
                        input_fields[tid].append(sf["field"])

            if "group_fields" in cfg:
                input_fields[tid].extend(cfg["group_fields"])

            if "header_field" in cfg and cfg["header_field"]:
                input_fields[tid].append(cfg["header_field"])

            if "data_field" in cfg and cfg["data_field"]:
                input_fields[tid].append(cfg["data_field"])

            if "sort_fields" in cfg:
                for sf in cfg["sort_fields"]:
                    if sf.get("field"):
                        input_fields[tid].append(sf["field"])

            # If current tool is a Join, do not expand beyond it for primary branch
            if tool.tool_type not in ("Join", "AlteryxBasePluginsGui.Join.Join"):
                for succ in graph.successors(curr):
                    queue.append(succ)

    # 3. Level 3: Inputs entering Left and Right side of Joins
    join_right_inputs: dict[int, int] = {}
    for conn in workflow.connections:
        join_tid = conn.destination_tool_id
        origin_tid = conn.origin_tool_id
        join_tool = workflow.tools.get(join_tid)
        if not join_tool or join_tool.tool_type not in ("Join", "AlteryxBasePluginsGui.Join.Join"):
            continue

        root_inputs = [inp for inp in input_tids if nx.has_path(graph, inp, origin_tid) or inp == origin_tid]
        if not root_inputs:
            continue
        root_tid = root_inputs[0]

        jcfg = join_tool.configuration.parsed or {}
        if conn.destination_anchor == "Left":
            if root_tid not in has_explicit_schema:
                for jf in jcfg.get("join_fields", []):
                    if jf.get("left"):
                        input_fields[root_tid].append(jf["left"])
        elif conn.destination_anchor == "Right":
            join_right_inputs[join_tid] = root_tid
            if root_tid not in has_explicit_schema:
                for jf in jcfg.get("join_fields", []):
                    if jf.get("right"):
                        input_fields[root_tid].append(jf["right"])

    # 4. Immediate downstream consumers for each join
    for join_tid, root_tid in join_right_inputs.items():
        if root_tid in has_explicit_schema:
            continue
        j_visited = set()
        j_queue = list(graph.successors(join_tid))
        while j_queue:
            j_curr = j_queue.pop(0)
            if j_curr in j_visited:
                continue
            j_visited.add(j_curr)

            j_tool = workflow.tools.get(j_curr)
            if not j_tool:
                continue
            j_cfg = j_tool.configuration.parsed or {}

            if j_tool.tool_type in ("Formula", "MultiFieldFormula"):
                for ff in j_cfg.get("formula_fields", []):
                    refs = _extract_referenced_fields(ff.get("expression", ""))
                    for rf in refs:
                        if rf not in input_fields[input_tids[0]] and rf not in input_fields[root_tid]:
                            input_fields[root_tid].append(rf)

            if j_tool.tool_type in ("Union", "BlockUntilDone", "Filter"):
                for succ in graph.successors(j_curr):
                    j_queue.append(succ)

    # 5. Generic placement for remaining unplaced fields
    all_known_fields = set()
    for tid, flds in input_fields.items():
        all_known_fields.update(flds)

    all_wf_fields = set()
    for tid, tool in workflow.tools.items():
        cfg = tool.configuration.parsed or {}
        if "summarize_fields" in cfg:
            for sf in cfg["summarize_fields"]:
                if sf.get("field"):
                    all_wf_fields.add(sf["field"])

    unplaced = all_wf_fields - all_known_fields
    if unplaced and len(input_tids) > 1:
        target_tid = input_tids[1]
        if target_tid not in has_explicit_schema:
            input_fields[target_tid].extend(sorted(unplaced))

    # 6. Final registry consolidation
    registry = {}
    for tid in input_tids:
        flds = list(dict.fromkeys(input_fields[tid]))
        registry[tid] = flds if flds else ["Record_Data"]

    return registry


def compute_tool_output_schema(
    tool: Tool,
    input_vars: list[str],
    stream_schemas: dict[str, list[str]],
    source_registry: dict[int, list[str]] | None = None,
    graph: nx.DiGraph | None = None,
    workflow: Workflow | None = None,
) -> dict[str, list[str]]:
    """Compute schema (list of column names) per output anchor of a tool."""
    cfg = tool.configuration.parsed or {}
    ttype = tool.tool_type
    primary_in = input_vars[0] if input_vars else None
    in_cols = list(stream_schemas.get(primary_in, [])) if primary_in else []

    # Source input data tools
    if source_registry is not None and tool.tool_id in source_registry:
        src_cols = list(source_registry[tool.tool_id])
        for f in tool.output_fields:
            if f.name and f.name not in src_cols:
                src_cols.append(f.name)
        for f in cfg.get("fields", []):
            if f and f not in src_cols:
                src_cols.append(f)
        return {"Output": src_cols}
    elif ttype in ("TextInput", "TextInputTranslator"):
        return {"Output": list(cfg.get("fields", []))}
    elif ttype in ("DateTimeNow", "DateTimeNowTranslator"):
        return {"Output": ["DateTimeNow"]}
    elif ttype in ("DbFileInput", "InputData", "Directory", "DynamicInput"):
        cols = [f.name for f in tool.output_fields if f.name] or list(cfg.get("fields", []))
        return {"Output": cols}
    elif ttype in ("Summarize", "SummarizeTranslator"):
        sfs = cfg.get("summarize_fields", [])
        out_cols = []
        for sf in sfs:
            act = sf.get("action", "").lower()
            ren = sf.get("rename", "")
            fld = sf.get("field", "")
            if act == "groupby":
                out_cols.append(ren if ren else fld)
            else:
                out_cols.append(ren if ren else f"{sf.get('action')}_{fld}")
        return {"Output": out_cols}
    elif ttype in ("AlteryxSelect", "Select", "SelectTranslator"):
        sfs = cfg.get("select_fields", [])
        if not sfs:
            return {"Output": in_cols}
        out_cols = []
        for sf in sfs:
            if sf.get("selected", "True") == "True" and not sf.get("field", "").startswith("*"):
                fld = sf.get("field", "")
                ren = sf.get("rename", "")
                out_cols.append(ren if ren else fld)
        return {"Output": out_cols}
    elif ttype in ("Formula", "FormulaTranslator"):
        ffs = cfg.get("formula_fields", [])
        out_cols = list(in_cols)
        for ff in ffs:
            fld = ff.get("field", "")
            if fld and fld not in out_cols:
                out_cols.append(fld)
        return {"Output": out_cols}
    elif ttype in ("Filter", "FilterTranslator"):
        return {"True": in_cols, "False": in_cols, "Output": in_cols}
    elif ttype in ("Sort", "SortTranslator", "Sample", "SampleTranslator", "Unique", "UniqueTranslator", "BlockUntilDone", "BrowseV2", "Browse", "Message"):
        return {"Output": in_cols, "Unique": in_cols, "Duplicates": in_cols, "Output1": in_cols, "Output2": in_cols, "Output3": in_cols}
    elif ttype in ("Join", "JoinTranslator"):
        left_in = input_vars[0] if len(input_vars) > 0 else None
        right_in = input_vars[1] if len(input_vars) > 1 else None
        left_cols = stream_schemas.get(left_in, []) if left_in else []
        right_cols = stream_schemas.get(right_in, []) if right_in else []

        joined_cols = list(left_cols)
        for rc in right_cols:
            if rc in left_cols:
                joined_cols.append(f"{rc}_right")
            else:
                joined_cols.append(rc)
        return {
            "Join": joined_cols,
            "Left": list(left_cols),
            "Right": list(right_cols),
        }
    elif ttype in ("Union", "UnionTranslator"):
        all_cols = []
        for iv in input_vars:
            for c in stream_schemas.get(iv, []):
                if c not in all_cols:
                    all_cols.append(c)
        return {"Output": all_cols}
    elif ttype in ("CrossTab", "CrossTabTranslator"):
        group_fields = list(cfg.get("group_fields", []))
        header_field = cfg.get("header_field", "")
        discovered_pivoted_cols = []
        if graph and workflow:
            for succ_tid in graph.successors(tool.tool_id):
                succ_tool = workflow.tools.get(succ_tid)
                if not succ_tool:
                    continue
                succ_cfg = succ_tool.configuration.parsed or {}
                if "select_fields" in succ_cfg:
                    for sf in succ_cfg["select_fields"]:
                        f_name = sf.get("rename") or sf.get("field")
                        if f_name and f_name not in group_fields and f_name != "*Unknown" and sf.get("selected", "True") != "False":
                            discovered_pivoted_cols.append(f_name)
        if not discovered_pivoted_cols:
            discovered_pivoted_cols = [f.name for f in tool.output_fields if f.name and f.name not in group_fields]
        if not discovered_pivoted_cols and header_field:
            discovered_pivoted_cols = [f"{header_field}_Values"]
        return {"Output": group_fields + discovered_pivoted_cols}
    else:
        return {"Output": in_cols}


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

    # Discover source input fields via DAG analysis
    source_registry = discover_source_fields(workflow, graph)

    # 3. Translate tools and collect explanations using dynamic stream environment
    stream_env: dict[tuple[int, str], str] = {}
    stream_schemas: dict[str, list[str]] = {}
    workflow._stream_schemas = stream_schemas  # type: ignore[attr-defined]

    translations: dict[int, TranslationResult] = {}
    tool_explanations: dict[int, ToolExplanation] = {}

    for tool_id in exec_order:
        tool = workflow.tools[tool_id]
        translator = get_translator(tool)
        input_vars = build_input_map(workflow, stream_env).get(tool_id, [])
        result = translator.translate(tool, input_vars, workflow)
        translations[tool_id] = result
        tool_explanations[tool_id] = translator.explain(tool, result)

        # Compute output schemas for this tool
        out_schemas = compute_tool_output_schema(tool, input_vars, stream_schemas, source_registry, graph, workflow)

        # Register output anchors in stream_env and stream_schemas
        for anchor, var_name in result.output_map.items():
            a_lower = anchor.lower()
            stream_env[(tool_id, a_lower)] = var_name
            if anchor in out_schemas:
                stream_schemas[var_name] = out_schemas[anchor]
            elif "Output" in out_schemas:
                stream_schemas[var_name] = out_schemas["Output"]

            if a_lower in ("output", "output1", "output2", "output3"):
                stream_env[(tool_id, "")] = var_name
                stream_env[(tool_id, "output")] = var_name
            elif a_lower in ("join", "j"):
                stream_env[(tool_id, "j")] = var_name
                stream_env[(tool_id, "join")] = var_name
            elif a_lower in ("left", "l"):
                stream_env[(tool_id, "l")] = var_name
                stream_env[(tool_id, "left")] = var_name
            elif a_lower in ("right", "r"):
                stream_env[(tool_id, "r")] = var_name
                stream_env[(tool_id, "right")] = var_name
            elif a_lower in ("true", "t"):
                stream_env[(tool_id, "t")] = var_name
                stream_env[(tool_id, "true")] = var_name
            elif a_lower in ("false", "f"):
                stream_env[(tool_id, "f")] = var_name
                stream_env[(tool_id, "false")] = var_name
            elif a_lower in ("join", "j"):
                stream_env[(tool_id, "j")] = var_name
                stream_env[(tool_id, "join")] = var_name
            elif a_lower in ("left", "l"):
                stream_env[(tool_id, "l")] = var_name
                stream_env[(tool_id, "left")] = var_name
            elif a_lower in ("right", "r"):
                stream_env[(tool_id, "r")] = var_name
                stream_env[(tool_id, "right")] = var_name
            elif a_lower in ("true", "t"):
                stream_env[(tool_id, "t")] = var_name
                stream_env[(tool_id, "true")] = var_name
            elif a_lower in ("false", "f"):
                stream_env[(tool_id, "f")] = var_name
                stream_env[(tool_id, "false")] = var_name

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
    input_node_ids: list[int] = []
    terminal_node_ids: list[int] = []
    business_output_node_ids: list[int] = []
    preview_tool_types = {"Browse", "BrowseV2", "Message", "Test"}

    sink_tids = set(n for n in graph.nodes() if graph.out_degree(n) == 0)

    for tid in exec_order:
        if tid in workflow.tools:
            tool = workflow.tools[tid]
            tdef = catalog.resolve(tool.plugin or tool.tool_type)
            if not tdef.input_anchors or tool.tool_type in ("DbFileInput", "InputData", "TextInput", "DynamicInput", "Directory", "DateTimeNow"):
                input_node_ids.append(tid)
            if tid in sink_tids or not tdef.output_anchors or tool.tool_type in ("DbFileOutput", "OutputData", "Browse", "BrowseV2", "Render"):
                if tid not in terminal_node_ids:
                    terminal_node_ids.append(tid)
                if tool.tool_type not in preview_tool_types and tid not in business_output_node_ids:
                    business_output_node_ids.append(tid)

    support_counts: dict[str, int] = {}
    for tr in translations.values():
        lvl = tr.support_level.value
        support_counts[lvl] = support_counts.get(lvl, 0) + 1

    metrics = WorkflowMetrics(
        total_nodes=len(workflow.tools),
        total_connections=len(workflow.connections),
        input_count=len(input_node_ids),
        output_count=len(terminal_node_ids),
        terminal_node_count=len(terminal_node_ids),
        terminal_node_ids=terminal_node_ids,
        business_output_count=len(business_output_node_ids),
        business_output_node_ids=business_output_node_ids,
        container_count=len(workflow.containers),
        annotation_count=len(workflow.textboxes),
        input_node_ids=input_node_ids,
        output_node_ids=terminal_node_ids,
        support_summary=support_counts,
    )

    # 9. Derive deterministic Business Intelligence Summary
    business_summary = generate_business_summary(workflow, graph, exec_order)

    # 10. Extract deterministic Source-to-Target Mapping (STTM)
    sttm = extract_sttm(workflow, graph, business_summary=business_summary)

    # 11. Enrich with LLM-authored full Business Report content if configured & available
    try:
        from awa.llm import get_default_generator
        import logging as _llm_log
        _llm_logger = _llm_log.getLogger("awa.llm")
        gen = get_default_generator()
        if gen.client.is_available:
            _llm_logger.info("LLM enrichment: starting generation for analysis %s", aid)

            # 1. Generate dynamic Process Stages for Overview page
            try:
                process_stages = gen.generate_process_stages(
                    workflow,
                    graph=graph,
                    business_summary=business_summary,
                    workflow_id=aid,
                )
                if process_stages:
                    business_summary.processing_stages = process_stages
            except Exception as stg_err:
                _llm_logger.warning("LLM process stages generation failed: %s", stg_err)

            # 2. Generate full Business Report content for DOCX
            report_content = gen.generate_business_report(workflow, business_summary, graph=graph, workflow_id=aid)
            if report_content is not None:
                _llm_logger.info("LLM enrichment: full business_report successfully generated")
                if report_content.workflow_description:
                    business_summary.one_line_purpose = report_content.workflow_description
                if report_content.executive_summary and business_summary.executive_summary:
                    business_summary.executive_summary.subject_and_purpose = report_content.executive_summary
                    business_summary.business_purpose = report_content.executive_summary
                if report_content.methods_of_analysis and business_summary.executive_summary:
                    business_summary.executive_summary.methods_and_process = report_content.methods_of_analysis
                if report_content.findings and business_summary.executive_summary:
                    business_summary.executive_summary.findings = report_content.findings
                if report_content.conclusions and business_summary.executive_summary:
                    business_summary.executive_summary.conclusions = report_content.conclusions

                # Populate LLM inputs (matched by count for structural alignment)
                if report_content.inputs:
                    for inp_llm, inp_bs in zip(report_content.inputs, business_summary.source_inputs):
                        if inp_llm.business_role:
                            inp_bs.business_role = inp_llm.business_role
                        if inp_llm.dependency_significance:
                            inp_bs.dependency_significance = inp_llm.dependency_significance

                # Populate LLM outputs
                if report_content.outputs:
                    for out_llm, out_bs in zip(report_content.outputs, business_summary.business_outputs):
                        if out_llm.what_it_represents:
                            out_bs.business_meaning = out_llm.what_it_represents
                        if out_llm.business_use:
                            out_bs.likely_use = out_llm.business_use

                # Replace business rules entirely with LLM-authored rules
                if report_content.business_rules:
                    from awa.model.business_summary import BusinessRule
                    new_rules = []
                    for r in report_content.business_rules:
                        new_rules.append(
                            BusinessRule(
                                rule_name=r.business_rule,
                                category=r.category,
                                description=r.business_rule,
                                evidence=r.evidence_configuration,
                            )
                        )
                    business_summary.business_rules = new_rules

                # Replace lineage entirely with LLM-authored lineage
                if report_content.lineage:
                    from awa.model.business_summary import BusinessLineageEntry
                    new_lineage = []
                    for l in report_content.lineage:
                        src_str = l.source_datasets if isinstance(l.source_datasets, str) else " + ".join(l.source_datasets)
                        new_lineage.append(
                            BusinessLineageEntry(
                                source_name=src_str,
                                transformation=l.major_business_transformation,
                                target_name=l.target_deliverable,
                                transformation_summary=f"{src_str} → {l.major_business_transformation} → {l.target_deliverable}",
                            )
                        )
                    business_summary.lineage = new_lineage
            else:
                _llm_logger.warning(
                    "LLM enrichment: full business_report generation returned None for analysis %s. "
                    "Report will use deterministic facts only — no LLM-authored prose.",
                    aid,
                )
        else:
            _llm_logger.debug("LLM enrichment: skipped — client not available (no runtime credentials)")
    except Exception as exc:
        import logging as _llm_log
        _llm_logger = _llm_log.getLogger("awa.llm")
        _llm_logger.warning(
            "LLM enrichment failed: %s — %s. Report will use deterministic facts only.",
            type(exc).__name__, str(exc)[:200],
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
        business_summary=business_summary,
        sttm=sttm,
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
        metrics=canonical.metrics,
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
        workflow, exec_order, translations, canonical.dag_layout, lineage_paths,
        business_summary=canonical.business_summary,
        analysis_id=canonical.analysis_id,
        graph=canonical.graph,
    )
    generate_docx(doc_model, output_dir / "workflow.docx", svg_content=svg_str)

    # 6. sttm.xlsx (Source-to-Target Mapping)
    if canonical.sttm:
        generate_sttm_excel(canonical.sttm, output_dir / "sttm.xlsx")

    # 7. tool_specifications.xlsx (Tool Specifications)
    gen = get_default_generator()
    tool_specs = gen.generate_all_tool_specifications(
        workflow,
        graph=canonical.graph,
        workflow_id=canonical.analysis_id,
    )
    tool_doc = build_tool_specifications_document(
        workflow=workflow,
        graph=canonical.graph,
        tool_specs=tool_specs,
    )
    generate_tool_specifications_excel(tool_doc, output_dir / "tool_specifications.xlsx")

    return AnalysisResult(
        workflow=workflow,
        execution_order=exec_order,
        translations=translations,
        output_dir=output_dir,
    )
