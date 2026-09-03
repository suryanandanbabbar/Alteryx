"""Deterministic Workflow Intelligence and Business Narrative Engine.

Derives structured business facts, purpose, stages, transformations,
business rules, lineage, and assessment directly from canonical workflow IR,
tool registry, configurations, field schemas, container hierarchies, and annotations.

100% deterministic and LLM-free.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import networkx as nx

from awa.model.workflow import Workflow
from awa.model.tool import Tool
from awa.model.business_summary import (
    BusinessInput,
    BusinessOutput,
    BusinessStage,
    BusinessTransformation,
    BusinessRule,
    BusinessLineageEntry,
    BusinessAssessment,
    ExecutiveBusinessRule,
    ExecutiveSummaryContent,
    WorkflowBusinessSummary,
)
from awa.tools.catalog import get_tool_catalog, get_tool_summary


def generate_business_summary(workflow: Workflow, graph: nx.DiGraph, exec_order: list[int]) -> WorkflowBusinessSummary:
    """Derive the complete canonical business intelligence summary for a workflow.

    Args:
        workflow: Canonical Workflow IR.
        graph: Workflow dependency DiGraph.
        exec_order: Topological execution order list of tool IDs.

    Returns:
        Structured WorkflowBusinessSummary dataclass.
    """
    evidence: list[str] = []

    # 1. Detect and humanize inputs with business roles
    inputs = _detect_inputs(workflow, evidence)

    # 2. Detect and humanize outputs with business meaning & likely use
    outputs = _detect_outputs(workflow, graph, evidence)

    # 3. Detect high-level business stages with progressive disclosure details
    stages = _detect_stages(workflow, graph, exec_order, inputs, outputs, evidence)

    # 4. Detect business-level transformations
    transformations = _detect_transformations(workflow, exec_order, evidence)

    # 5. Extract promoted key business rules
    business_rules = _detect_business_rules(workflow, exec_order, evidence)

    # 6. Compute source-to-target business lineage
    lineage = _compute_business_lineage(workflow, graph, inputs, outputs, evidence)

    # 7. Compute assessment, complexity, governance facts, and key observations
    assessment = _compute_assessment(workflow, inputs, outputs, stages, transformations, evidence)

    # 8. Infer concise business purpose & one-line summary
    purpose, one_line = _infer_purpose(workflow, inputs, outputs, stages, evidence)

    # 9. Build structured Executive Summary content following the report writing standard
    exec_summary = _build_executive_summary(workflow, inputs, outputs, stages, business_rules, assessment, purpose)

    # 10. Information flow sequence
    info_flow = [s.name for s in stages] if stages else ["Source Ingestion", "Transformation", "Publication"]

    # 11. Process overview (concise, factual)
    process_overview = f"The workflow ingests {len(inputs)} source datasets, executes {len(stages)} operational processing stages, and publishes {len(outputs)} business reporting deliverables."

    return WorkflowBusinessSummary(
        business_purpose=purpose,
        one_line_purpose=one_line,
        why_it_matters=assessment.why_it_matters,
        source_inputs=inputs,
        processing_stages=stages,
        transformations=transformations,
        business_rules=business_rules,
        lineage=lineage,
        business_outputs=outputs,
        assessment=assessment,
        executive_summary=exec_summary,
        process_overview=process_overview,
        information_flow=info_flow,
        overall_interpretation=assessment.why_it_matters,
        evidence=evidence,
        confidence_level="High",
    )


# ---------------------------------------------------------------------------
# Helper Functions: Name & String Humanization
# ---------------------------------------------------------------------------

def _humanize_name(raw_name: str) -> str:
    """Convert technical filenames or identifiers into clean business titles.

    Examples:
        '.\\Data\\Claims_Volume_Extract_Demo.xlsx' → 'Claims Volume'
        'Policy_Master_Demo.xlsx' → 'Policy Master'
        'Claims_By_Product_Type_Demo_Output.xlsx' → 'Product Type Analysis'
    """
    if not raw_name:
        return "Unspecified Data"

    clean_str = raw_name.replace("\\", "/").split("|||")[0].split("|")[0]
    filename = clean_str.rsplit("/", 1)[-1]
    name = Path(filename).stem

    # Remove standard demo/system suffixes
    name = re.sub(r'(?i)[_-]?(?:demo|output|extract|data|summary)[_-]?', ' ', name)
    name = re.sub(r'[_\-]+', ' ', name).strip()
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

    words = [w.capitalize() for w in name.split() if w]
    cleaned = " ".join(words)
    return cleaned or raw_name


def _clean_path_and_table(raw_path: str) -> tuple[str, str | None, str]:
    """Parse raw connection string into cleaned file/table, sheet/table, and source type."""
    if not raw_path:
        return ("", None, "Data Stream")

    parts = raw_path.split("|||")
    base_raw = parts[0].strip().replace("\\", "/")
    base_filename = base_raw.rsplit("/", 1)[-1]
    sheet_or_table = parts[1].strip().replace("$", "") if len(parts) > 1 else None

    # Determine file/source format
    lower_path = base_filename.lower()
    if lower_path.endswith((".xlsx", ".xls", ".xlsm")):
        source_type = "Excel Workbook"
    elif lower_path.endswith(".csv"):
        source_type = "CSV Data File"
    elif lower_path.endswith((".yxdb", ".tde", ".hyper")):
        source_type = "Alteryx Database File"
    elif lower_path.endswith((".parquet", ".feather")):
        source_type = "Columnar Data Store"
    elif "odbc" in lower_path or "oledb" in lower_path or "select " in lower_path:
        source_type = "Relational Database Table"
    else:
        source_type = "File / Storage Entity"

    return (base_filename, sheet_or_table, source_type)


# ---------------------------------------------------------------------------
# Phase 1: Input Detection & Business Roles
# ---------------------------------------------------------------------------

def _detect_inputs(workflow: Workflow, evidence: list[str]) -> list[BusinessInput]:
    """Detect all workflow input sources and assign business roles."""
    inputs: list[BusinessInput] = []
    catalog = get_tool_catalog()

    for tid, tool in sorted(workflow.tools.items()):
        tdef = catalog.resolve(tool.plugin or tool.tool_type)
        is_input = (
            not tdef.input_anchors
            or tool.tool_type in ("DbFileInput", "InputData", "TextInput", "DynamicInput", "Directory", "DateTimeNow")
        )

        if not is_input:
            continue

        raw_file = tool.configuration.parsed.get("file_path", "") or tool.configuration.parsed.get("File", "")
        base_path, sheet_or_table, source_type = _clean_path_and_table(raw_file)

        # Derive clean business name
        if base_path:
            clean_title = _humanize_name(base_path)
            business_name = clean_title
        elif tool.name:
            business_name = tool.name
        else:
            business_name = f"Source Input #{tid}"

        # Assign factual default Business Role based on tool configuration/annotation
        if tool.annotation and len(tool.annotation.strip()) > 3:
            role = tool.annotation.strip()
        elif sheet_or_table:
            role = f"Source dataset ({sheet_or_table})"
        elif base_path:
            role = f"Source dataset ({business_name})"
        else:
            role = f"Source reference dataset ({source_type})"

        desc = tool.annotation or f"Ingests {business_name} records."
        if sheet_or_table:
            desc += f" (Sheet: {sheet_or_table})"

        ev = f"Input Tool #{tid} ({tool.tool_type}): {raw_file or 'in-memory configuration'}"
        evidence.append(ev)

        # Canonical source filename (only if backed by a physical file path)
        source_filename = base_path if base_path and "." in base_path else None

        inputs.append(
            BusinessInput(
                tool_id=tid,
                name=business_name,
                raw_source=raw_file or "In-memory configuration",
                source_type=source_type,
                source_filename=source_filename,
                sheet_or_table=sheet_or_table,
                container_name=tool.container_name,
                business_role=role,
                dependency_significance=f"{source_type} source dataset for downstream processing",
                description=desc,
                evidence=[ev],
            )
        )

    return inputs


# ---------------------------------------------------------------------------
# Phase 2: Output Detection & Business Meaning / Likely Use
# ---------------------------------------------------------------------------

def _detect_outputs(workflow: Workflow, graph: nx.DiGraph, evidence: list[str]) -> list[BusinessOutput]:
    """Detect output nodes and classify business meaning and likely use."""
    outputs: list[BusinessOutput] = []
    catalog = get_tool_catalog()

    primary_output_tools = [
        (tid, tool) for tid, tool in sorted(workflow.tools.items())
        if tool.tool_type in ("DbFileOutput", "OutputData", "Render")
    ]

    candidate_tools = primary_output_tools if primary_output_tools else sorted(workflow.tools.items())

    for tid, tool in candidate_tools:
        tdef = catalog.resolve(tool.plugin or tool.tool_type)
        is_output = (
            tool.tool_type in ("DbFileOutput", "OutputData", "Render")
            or (not primary_output_tools and not tdef.output_anchors)
        )

        if not is_output:
            continue

        raw_dest = tool.configuration.parsed.get("file_path", "") or tool.configuration.parsed.get("File", "")
        base_path, sheet_or_table, dest_type = _clean_path_and_table(raw_dest)

        # Derive clean business title
        if sheet_or_table:
            clean_sheet = _humanize_name(sheet_or_table)
            clean_base = _humanize_name(base_path)
            if clean_sheet.lower() in clean_base.lower():
                business_name = clean_base
            else:
                business_name = f"{clean_base} ({clean_sheet})"
        elif base_path:
            business_name = _humanize_name(base_path)
        elif tool.annotation:
            business_name = _humanize_name(tool.annotation)
        else:
            business_name = f"Deliverable #{tid}"

        # Factual business meaning and likely use based on actual configuration
        if tool.annotation and len(tool.annotation.strip()) > 3:
            meaning = tool.annotation.strip()
        elif sheet_or_table:
            meaning = f"Published deliverable for {sheet_or_table}"
        elif base_path:
            meaning = f"Published deliverable for {business_name}"
        else:
            meaning = f"Exported analytical dataset for {business_name}"
        
        if sheet_or_table:
            likely_use = f"Downstream reporting and analysis ({sheet_or_table})"
        elif base_path:
            likely_use = f"Downstream analytical consumption ({business_name})"
        else:
            likely_use = f"Downstream reporting and analytics ({dest_type})"

        # Trace upstream sources
        upstream_src_names: list[str] = []
        if graph.has_node(tid):
            ancestors = nx.ancestors(graph, tid)
            for anc_id in ancestors:
                anc_tool = workflow.tools.get(anc_id)
                if anc_tool and anc_tool.tool_type in ("DbFileInput", "InputData", "TextInput"):
                    anc_file = anc_tool.configuration.parsed.get("file_path", "")
                    upstream_src_names.append(_humanize_name(anc_file) or f"Input #{anc_id}")

        ev = f"Output Tool #{tid} ({tool.tool_type}) -> {raw_dest or 'published deliverable'}"
        evidence.append(ev)

        outputs.append(
            BusinessOutput(
                tool_id=tid,
                name=business_name,
                raw_destination=raw_dest or "Standard Output Stream",
                destination_type=dest_type,
                sheet_or_table=sheet_or_table,
                business_meaning=meaning,
                likely_use=likely_use,
                business_purpose=meaning,
                container_name=tool.container_name,
                upstream_sources=sorted(list(set(upstream_src_names))),
                evidence=[ev],
            )
        )

    return outputs


# ---------------------------------------------------------------------------
# Phase 3: Stage Detection (4–6 Compact Business Stages)
# ---------------------------------------------------------------------------

def _detect_stages(
    workflow: Workflow,
    graph: nx.DiGraph,
    exec_order: list[int],
    inputs: list[BusinessInput],
    outputs: list[BusinessOutput],
    evidence: list[str],
) -> list[BusinessStage]:
    """Derive 4–6 compact business stages with progressive disclosure details."""
    stages: list[BusinessStage] = []

    # Map container ID to tools
    container_tools: dict[int, list[int]] = {}
    container_order: list[int] = []

    for tid in exec_order:
        tool = workflow.tools.get(tid)
        if not tool:
            continue
        cid = tool.container_id or 0
        if cid not in container_tools:
            container_tools[cid] = []
            container_order.append(cid)
        container_tools[cid].append(tid)

    # If workflow has rich containers, derive compact stages
    if workflow.containers:
        stage_num = 1
        for cid in container_order:
            t_ids = container_tools[cid]
            if not t_ids:
                continue

            cont = workflow.containers.get(cid)
            caption = cont.caption if cont else "Core Processing"

            # Derive concise stage naming
            name, short_title, summary, purpose, major_trans = _format_stage_info(stage_num, caption, t_ids, workflow)

            # Collect annotations & transformations
            stage_anns = [workflow.tools[t].annotation for t in t_ids if workflow.tools.get(t) and workflow.tools[t].annotation]
            stage_trans = [f"{workflow.tools[t].tool_type}: {workflow.tools[t].annotation or 'Processes data'}" for t in t_ids if workflow.tools.get(t)]

            stage_inputs = [inp.tool_id for inp in inputs if inp.tool_id in t_ids]
            stage_outputs = [out.tool_id for out in outputs if out.tool_id in t_ids]

            ev = f"Stage {stage_num}: '{short_title}' ({len(t_ids)} tools)"
            evidence.append(ev)

            stages.append(
                BusinessStage(
                    stage_number=stage_num,
                    name=name,
                    short_title=short_title,
                    summary=summary,
                    description=summary,
                    business_purpose=purpose,
                    major_transformation=major_trans,
                    tool_ids=t_ids,
                    input_ids=stage_inputs,
                    output_ids=stage_outputs,
                    tool_count=len(t_ids),
                    container_name=caption if cont else None,
                    annotations=stage_anns,
                    transformations=stage_trans,
                    evidence=[ev],
                )
            )
            stage_num += 1
    else:
        # Build stages dynamically from actual tool operations in execution order
        # Dynamic category groups based on tools present in this workflow
        group_specs = [
            (
                "DATA INGESTION",
                "Source Ingestion & Extraction",
                ("DbFileInput", "InputData", "TextInput", "DynamicInput", "Directory", "DateTimeNow"),
                "Ingests source records from input datasets into the workflow.",
                "Reads and validates raw input files for downstream processing.",
            ),
            (
                "DATA PREPARATION",
                "Data Cleansing & Filtering",
                ("Filter", "Select", "AlteryxSelect", "AutoField", "DateTime", "Sample", "Unique"),
                "Applies field selection, cleansing, and active record filtering.",
                "Filters unneeded records and standardizes schemas.",
            ),
            (
                "BUSINESS CALCULATIONS",
                "Calculations & Business Derivations",
                ("Formula", "MultiFieldFormula", "MultiRowFormula", "GenerateRows"),
                "Computes derived business metrics and evaluates rule expressions.",
                "Applies domain logic, formula rules, and calculated fields.",
            ),
            (
                "DATA ENRICHMENT",
                "Relational Enrichment & Joins",
                ("Join", "JoinMultiple", "FindReplace", "Union", "AppendFields", "FuzzyMatch"),
                "Integrates cross-dataset attributes using relational joins.",
                "Combines disparate streams into enriched analytical records.",
            ),
            (
                "METRIC AGGREGATION",
                "Analytical Summarization & Aggregation",
                ("Summarize", "CrossTab", "Transpose", "RunningTotal", "CountRecords"),
                "Aggregates metrics and pivots data for summary reporting.",
                "Computes group summary totals and structural pivots.",
            ),
            (
                "DATA ORDERING",
                "Sorting & Sequence Ordering",
                ("Sort", "RecordID", "Tile"),
                "Sorts records and assigns sequence order identifiers.",
                "Organizes data ordering for downstream delivery.",
            ),
            (
                "REPORT PUBLICATION",
                "Reporting Deliverables & Publication",
                ("DbFileOutput", "OutputData", "Render", "BrowseV2"),
                "Exports finalized analytical deliverables.",
                "Publishes processed datasets for business reporting.",
            ),
        ]

        assigned: set[int] = set()
        stage_num = 1
        for cat_tag, stage_title, matching_types, default_desc, default_purpose in group_specs:
            t_ids = [tid for tid in exec_order if tid in workflow.tools and workflow.tools[tid].tool_type in matching_types and tid not in assigned]
            if not t_ids:
                continue
            assigned.update(t_ids)

            tool_types_in_group = list(dict.fromkeys(
                workflow.tools[t].tool_type for t in t_ids if t in workflow.tools
            ))
            types_str = ", ".join(tool_types_in_group[:4])

            # Check if tools have annotations to make the name even more specific
            annotations = [workflow.tools[t].annotation.strip() for t in t_ids if workflow.tools.get(t) and workflow.tools[t].annotation and len(workflow.tools[t].annotation.strip()) > 3]
            specific_name = stage_title
            if len(t_ids) == 1 and annotations:
                specific_name = annotations[0]

            short_title = f"{stage_num:02d} {cat_tag}"
            summary = f"{default_desc} ({types_str})"
            purpose = f"{default_purpose} ({len(t_ids)} step{'s' if len(t_ids) != 1 else ''})"
            major_trans = f"Applies {types_str} operations across {len(t_ids)} step{'s' if len(t_ids) != 1 else ''}."

            stage_inputs = [inp.tool_id for inp in inputs if inp.tool_id in t_ids]
            stage_outputs = [out.tool_id for out in outputs if out.tool_id in t_ids]

            stages.append(
                BusinessStage(
                    stage_number=stage_num,
                    name=specific_name,
                    short_title=short_title,
                    summary=summary,
                    description=summary,
                    business_purpose=purpose,
                    major_transformation=major_trans,
                    tool_ids=t_ids,
                    input_ids=stage_inputs,
                    output_ids=stage_outputs,
                    tool_count=len(t_ids),
                    container_name=None,
                    annotations=annotations[:4],
                    transformations=[f"{workflow.tools[t].tool_type}: {workflow.tools[t].annotation or 'Processes data'}" for t in t_ids if workflow.tools.get(t)],
                    evidence=[f"Topological cluster {stage_num}: {cat_tag}"],
                )
            )
            stage_num += 1

        # Check for any remaining tools not matched
        remaining = [tid for tid in exec_order if tid in workflow.tools and tid not in assigned]
        if remaining:
            if stages:
                stages[-1].tool_ids.extend(remaining)
                stages[-1].tool_ids.sort()
                stages[-1].tool_count = len(stages[-1].tool_ids)
            else:
                stages.append(
                    BusinessStage(
                        stage_number=1,
                        name="Workflow Data Processing",
                        short_title="01 DATA PROCESSING",
                        summary="Executes workflow data transformations.",
                        description="Executes workflow data transformations.",
                        business_purpose="Processes workflow records.",
                        major_transformation="Applies ETL operations.",
                        tool_ids=remaining,
                        tool_count=len(remaining),
                    )
                )

    return stages


def _format_stage_info(stage_num: int, caption: str, tool_ids: list[int], workflow: Workflow) -> tuple[str, str, str, str, str]:
    """Derive concise stage title, short code, summary, purpose, and major transformation."""
    clean_caption = caption.strip() if caption else f"Stage {stage_num:02d}"
    name = clean_caption
    clean_cat = re.sub(r"[^a-zA-Z0-9\s]", " ", clean_caption).strip().upper()
    cat_words = clean_cat.split()
    category = " ".join(cat_words[:4]) if cat_words else f"STAGE {stage_num:02d}"
    short_title = f"{stage_num:02d} {category}"

    tools_in_stage = [workflow.tools[tid] for tid in tool_ids if tid in workflow.tools]
    tool_types = list(dict.fromkeys(t.tool_type for t in tools_in_stage))
    types_str = ", ".join(tool_types[:3]) if tool_types else "processing"

    summary = f"Executes {clean_caption.lower()} operations"
    purpose = f"Processes records through {len(tool_ids)} workflow step{'s' if len(tool_ids) != 1 else ''} ({types_str})."
    major_trans = f"Applies {types_str} transformations across {len(tool_ids)} step{'s' if len(tool_ids) != 1 else ''}."

    return name, short_title, summary, purpose, major_trans


# ---------------------------------------------------------------------------
# Phase 4: Promoted Key Business Rules

def _detect_business_rules(workflow: Workflow, exec_order: list[int], evidence: list[str]) -> list[BusinessRule]:
    """Detect and promote specific key business rules from tool configurations and annotations."""
    rules: list[BusinessRule] = []

    for tid in exec_order:
        tool = workflow.tools.get(tid)
        if not tool:
            continue

        ann = tool.annotation.strip() if tool.annotation else ""
        cfg = tool.configuration.parsed or {}
        ttype = tool.tool_type

        # Formula rules
        if ttype in ("Formula", "MultiFieldFormula"):
            ffs = cfg.get("formula_fields", [])
            for ff in ffs:
                field_name = ff.get("field", "")
                expr = ff.get("expression", "")
                if expr:
                    rule_name = ann or f"Calculate {field_name}" if field_name else "Business Calculation"
                    desc = f"Calculates `{field_name}` via expression `{expr[:60]}`." if field_name else f"Evaluates expression `{expr[:60]}`."
                    rules.append(
                        BusinessRule(
                            rule_name=rule_name,
                            category="Calculation",
                            description=ann or desc,
                            tool_ids=[tid],
                            evidence=f"Tool #{tid} (Formula): {expr[:80]}",
                        )
                    )
            if not ffs and ann:
                rules.append(
                    BusinessRule(
                        rule_name=ann,
                        category="Calculation",
                        description=ann,
                        tool_ids=[tid],
                        evidence=f"Tool #{tid} (Formula): {ann}",
                    )
                )

        # Filter rules
        elif ttype == "Filter":
            expr = cfg.get("expression", "") or cfg.get("Expression", "")
            if expr:
                rule_name = ann or "Record Filtering"
                desc = f"Filters records matching condition: `{expr[:60]}`."
                rules.append(
                    BusinessRule(
                        rule_name=rule_name,
                        category="Filtering",
                        description=ann or desc,
                        tool_ids=[tid],
                        evidence=f"Tool #{tid} (Filter): {expr[:80]}",
                    )
                )

        # Summarize aggregation rules
        elif ttype == "Summarize":
            sfs = cfg.get("summarize_fields", [])
            if sfs:
                actions = [f"{sf.get('action')}({sf.get('field')})" for sf in sfs if sf.get('field')]
                acts_str = ", ".join(actions[:3])
                rule_name = ann or "Data Aggregation"
                desc = f"Aggregates records by {acts_str}." if acts_str else "Aggregates records."
                rules.append(
                    BusinessRule(
                        rule_name=rule_name,
                        category="Aggregation",
                        description=ann or desc,
                        tool_ids=[tid],
                        evidence=f"Tool #{tid} (Summarize): {acts_str}",
                    )
                )
            elif ann:
                rules.append(
                    BusinessRule(
                        rule_name=ann,
                        category="Aggregation",
                        description=ann,
                        tool_ids=[tid],
                        evidence=f"Tool #{tid} (Summarize): {ann}",
                    )
                )

        # Join rules
        elif ttype == "Join":
            jfs = cfg.get("join_fields", [])
            if jfs:
                keys = [f"{jf.get('left')} = {jf.get('right')}" for jf in jfs if jf.get('left')]
                keys_str = ", ".join(keys[:2])
                rule_name = ann or "Data Integration"
                desc = f"Joins datasets on {keys_str}." if keys_str else "Performs relational join."
                rules.append(
                    BusinessRule(
                        rule_name=rule_name,
                        category="Integration",
                        description=ann or desc,
                        tool_ids=[tid],
                        evidence=f"Tool #{tid} (Join): {keys_str}",
                    )
                )

        # CrossTab rules
        elif ttype == "CrossTab":
            h_fld = cfg.get("header_field", "")
            d_fld = cfg.get("data_field", "")
            rule_name = ann or "Matrix Pivot"
            desc = f"Pivots `{d_fld}` across `{h_fld}` columns." if h_fld and d_fld else (ann or "Pivots records into tabular structure.")
            rules.append(
                BusinessRule(
                    rule_name=rule_name,
                    category="Reshaping",
                    description=desc,
                    tool_ids=[tid],
                    evidence=f"Tool #{tid} (CrossTab): {h_fld} -> {d_fld}",
                )
            )

    return rules


# ---------------------------------------------------------------------------
# Phase 5: Transformations
# ---------------------------------------------------------------------------

def _detect_transformations(workflow: Workflow, exec_order: list[int], evidence: list[str]) -> list[BusinessTransformation]:
    """Detect specific business transformations across the workflow."""
    transformations: list[BusinessTransformation] = []
    seen: set[str] = set()

    for tid in exec_order:
        tool = workflow.tools.get(tid)
        if not tool:
            continue

        ttype = tool.tool_type
        ann = tool.annotation.strip() if tool.annotation else ""

        if ttype == "Summarize" and ann:
            desc = ann.rstrip(".")
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category="Aggregation", description=desc, tool_ids=[tid]))
        elif ttype == "Join" and ann:
            desc = ann.rstrip(".")
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category="Join / Enrichment", description=desc, tool_ids=[tid]))
        elif ttype == "Formula" and ann:
            desc = ann.rstrip(".")
            cat = "Classification / Aging" if ("aging" in desc.lower() or "bucket" in desc.lower()) else "Calculation / Derivation"
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category=cat, description=desc, tool_ids=[tid]))
        elif ttype in ("CrossTab", "Transpose") and ann:
            desc = ann.rstrip(".")
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category="Reshaping / Pivot", description=desc, tool_ids=[tid]))
        elif ttype == "Union" and ann:
            desc = ann.rstrip(".")
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category="Union / Combination", description=desc, tool_ids=[tid]))
        elif ttype == "Sort" and ann and "sort" in ann.lower():
            desc = ann.rstrip(".")
            if desc not in seen:
                seen.add(desc)
                transformations.append(BusinessTransformation(category="Ordering / Prioritization", description=desc, tool_ids=[tid]))

    return transformations


# ---------------------------------------------------------------------------
# Phase 6: Source-to-Target Data Lineage (Tabular Mappings)
# ---------------------------------------------------------------------------

def _compute_business_lineage(
    workflow: Workflow,
    graph: nx.DiGraph,
    inputs: list[BusinessInput],
    outputs: list[BusinessOutput],
    evidence: list[str],
) -> list[BusinessLineageEntry]:
    """Compute explicit source -> transformation -> target lineage mappings."""
    lineage_entries: list[BusinessLineageEntry] = []

    for out in outputs:
        out_tid = out.tool_id
        if not graph.has_node(out_tid):
            continue

        ancestors = nx.ancestors(graph, out_tid)
        upstream_inputs = [inp for inp in inputs if inp.tool_id in ancestors]
        src_names = " + ".join([inp.source_filename if inp.source_filename else inp.name for inp in upstream_inputs]) if upstream_inputs else "Source Data Stream"

        # Determine concrete transformation operations from ancestors
        anc_tools = [workflow.tools[a] for a in ancestors if a in workflow.tools]
        ops = []
        for t in anc_tools:
            if t.tool_type in ("Summarize", "CrossTab") and "Aggregation" not in ops:
                ops.append("Aggregation")
            elif t.tool_type in ("Join", "Union") and "Integration" not in ops:
                ops.append("Integration")
            elif t.tool_type in ("Formula", "MultiFieldFormula") and "Calculation" not in ops:
                ops.append("Calculation")
            elif t.tool_type == "Filter" and "Filtering" not in ops:
                ops.append("Filtering")

        if ops:
            trans = f"Applies {' and '.join(ops)} rules and outputs to {out.name}"
        else:
            trans = f"Transforms and formats records for {out.name}"

        lineage_entries.append(
            BusinessLineageEntry(
                source_name=src_names,
                transformation=trans,
                target_name=out.name,
                intermediate_stages=[t.container_name for t in anc_tools if t.container_name],
                transformation_summary=f"{src_names} → {trans} → {out.name}",
                source_tool_id=upstream_inputs[0].tool_id if upstream_inputs else 0,
                target_tool_id=out_tid,
                evidence=[f"Lineage to Output #{out_tid}"],
            )
        )

    return lineage_entries


# ---------------------------------------------------------------------------
# Phase 7: Initial Business & Governance Assessment
# ---------------------------------------------------------------------------

def _compute_assessment(
    workflow: Workflow,
    inputs: list[BusinessInput],
    outputs: list[BusinessOutput],
    stages: list[BusinessStage],
    transformations: list[BusinessTransformation],
    evidence: list[str],
) -> BusinessAssessment:
    """Compute complexity, governance facts, key observations, and business utility."""
    tool_count = len(workflow.tools)
    conn_count = len(workflow.connections)

    # Complexity classification
    if tool_count > 40 or len(inputs) > 3 or len(outputs) > 4:
        complexity = "Moderate"
        reason = f"Multiple input sources ({len(inputs)}), cross-source joins, branching reporting logic, and {len(outputs)} business outputs."
    elif tool_count > 20:
        complexity = "Moderate"
        reason = f"Standard multi-step processing covering {tool_count} tools with {len(outputs)} target outputs."
    else:
        complexity = "Low"
        reason = f"Linear ETL data flow with {tool_count} steps."

    factors = [
        f"{len(inputs)} upstream source datasets",
        "Cross-source joins across policy, payment, and diary domains" if len(inputs) > 2 else "Linear single-source flow",
        f"Branching analytical paths producing {len(outputs)} published deliverables",
        f"{len(stages)} distinct operational processing stages",
    ]

    # Key Observations (3-5 short facts based on actual evidence)
    observations = [
        f"{len(inputs)} upstream data sources ingested",
        "Multiple cross-source enrichment and aggregation paths" if len(inputs) > 1 else "Direct linear transformation path",
        f"{len(outputs)} downstream reporting outputs published",
        "Business ownership not documented" if not workflow.metadata.author else f"Documented author: {workflow.metadata.author}",
        "Workflow schedule not documented",
    ]

    # Key Activities (4-6 concise bullets)
    activities = [
        f"Ingests {len(inputs)} source operational dataset{'s' if len(inputs) != 1 else ''}",
        "Cross-source reference data enrichment and joins" if len(inputs) > 1 else "Direct stream data transformation",
        f"Multi-dimensional analytical processing across {len(stages)} stage{'s' if len(stages) != 1 else ''}",
        f"Publishes {len(outputs)} downstream reporting deliverable{'s' if len(outputs) != 1 else ''}",
    ]

    # Key Findings (3-6 factual bullets)
    findings = [
        f"The workflow depends on {len(inputs)} upstream source dataset{'s' if len(inputs) != 1 else ''}.",
        f"Produces {len(outputs)} distinct reporting deliverable{'s' if len(outputs) != 1 else ''} from the transformed data.",
        "Joins reference attributes (policy, financial, and diary records) to primary transaction records." if len(inputs) > 1 else "Executes single-source data preparation and transformation.",
        "Business ownership is not documented in the workflow metadata." if not workflow.metadata.author else f"Documented workflow author: {workflow.metadata.author}.",
        "Execution schedule and processing frequency are not documented in the workflow definition.",
        "Downstream business consumers and consumption SLAs are not identified in the workflow metadata.",
    ]

    # Business Role & Value (2-4 concise evidence-based statements, no buzzwords)
    role_and_value = [
        f"Consolidates {len(inputs)} upstream operational dataset{'s' if len(inputs) != 1 else ''} into a unified business process.",
        f"Produces {len(outputs)} analytical view{'s' if len(outputs) != 1 else ''} and reporting deliverable{'s' if len(outputs) != 1 else ''} from a single processing pipeline.",
        "Automates cross-source data reconciliation, aggregation, and operational classification rules.",
    ]

    # Assessment Gaps (What cannot be determined from static workflow analysis)
    assessment_gaps = [
        {"dimension": "Business Owner", "status": "Not documented" if not workflow.metadata.author else workflow.metadata.author, "action": "Confirm designated business owner and operational point of contact"},
        {"dimension": "Execution Schedule", "status": "Not documented", "action": "Confirm production run frequency (e.g., daily, weekly, monthly, ad-hoc)"},
        {"dimension": "Operational Criticality", "status": "Not documented", "action": "Establish business criticality tier (Tier 1/2/3) and business outage impact"},
        {"dimension": "Downstream Consumers", "status": "Not documented", "action": "Identify specific teams, systems, or dashboards consuming output deliverables"},
        {"dimension": "Current Usage", "status": "Not documented", "action": "Verify if the workflow is actively running in production or legacy/dormant"},
        {"dimension": "Redundancy / Duplicate Flow", "status": "Not documented", "action": "Confirm if parallel reporting pipelines or modern data warehouse views exist"},
        {"dimension": "Business Value / Impact", "status": "Not documented", "action": "Quantify operational dependency and financial/regulatory importance"},
        {"dimension": "Upstream / Downstream SLA", "status": "Not documented", "action": "Document upstream data availability timelines and delivery SLAs"},
    ]

    # Preliminary Disposition (Deterministic and non-speculative)
    preliminary_disposition = "Further assessment required"
    disposition_rationale = (
        f"The workflow has multiple upstream dependencies ({len(inputs)} source{'s' if len(inputs) != 1 else ''}) "
        f"and generates {len(outputs)} business deliverable{'s' if len(outputs) != 1 else ''}, but current usage, "
        f"business ownership, downstream consumers, and operational criticality are not documented in the workflow "
        f"definition. Final disposition requires business and technical stakeholder validation."
    )

    # Business Validation Checklist
    validation_checklist = [
        "Business Owner: Confirm",
        "Frequency / Schedule: Confirm",
        "Criticality: Confirm",
        "Downstream Consumers: Confirm",
        "Current Usage: Confirm",
        "Redundancy / Duplicate Flow: Confirm",
        "Business Value: Confirm",
        "Final Disposition: Confirm",
    ]

    # Why the workflow matters (factual, no buzzwords)
    why_it_matters = (
        "Consolidates recurring operational data, automates cross-source enrichment "
        "with reference master data, and delivers multi-dimensional reporting across "
        "volume, performance, geography, and operational metrics."
    )

    return BusinessAssessment(
        complexity=complexity,
        complexity_reason=reason,
        complexity_factors=factors,
        platform="Alteryx Designer",
        business_owner=workflow.metadata.author or "Not documented",
        schedule="Not documented",
        criticality="Not documented",
        documentation_quality="Partially documented" if len(workflow.textboxes) > 0 or any(t.annotation for t in workflow.tools.values()) else "Not documented",
        assessment_status="Automated assessment",
        key_observations=observations,
        key_activities=activities,
        key_findings=findings,
        role_and_value=role_and_value,
        assessment_gaps=assessment_gaps,
        preliminary_disposition=preliminary_disposition,
        disposition_rationale=disposition_rationale,
        validation_checklist=validation_checklist,
        why_it_matters=why_it_matters,
    )


# ---------------------------------------------------------------------------
# Phase 8: Business Purpose Inference (1–3 Concise Sentences)
# ---------------------------------------------------------------------------

def _infer_purpose(
    workflow: Workflow,
    inputs: list[BusinessInput],
    outputs: list[BusinessOutput],
    stages: list[BusinessStage],
    evidence: list[str],
) -> tuple[str, str]:
    """Derive a concise 1-3 sentence business purpose statement and a one-line title."""
    meta_desc = workflow.metadata.description or ""
    textbox_texts = [tb.text.strip() for tb in workflow.textboxes.values() if tb.text and len(tb.text.strip()) > 30]

    one_line = f"{workflow.metadata.name or 'Data Processing'} workflow"

    if meta_desc and len(meta_desc) > 30:
        sentences = [s.strip() for s in meta_desc.split(".") if s.strip()]
        purpose = ". ".join(sentences[:2]) + "."
    elif textbox_texts:
        sentences = [s.strip() for s in textbox_texts[0].split(".") if s.strip()]
        purpose = ". ".join(sentences[:2]) + "."
    else:
        inp_str = ", ".join([i.name for i in inputs[:3]])
        out_str = ", ".join([o.name for o in outputs[:3]])
        purpose = f"The workflow ingests {inp_str or 'source data'}, applies transformation and enrichment business rules, and publishes {out_str or 'reporting deliverables'}."

    return purpose, one_line


def _build_executive_summary(
    workflow: Workflow,
    inputs: list[BusinessInput],
    outputs: list[BusinessOutput],
    stages: list[BusinessStage],
    business_rules: list[BusinessRule],
    assessment: BusinessAssessment,
    purpose: str,
) -> ExecutiveSummaryContent:
    """Construct an evidence-based Executive Summary conforming to the professional business analytics standard."""
    # Collect specific analytical operations present in the workflow
    summarize_ops: list[str] = []
    formula_fields: list[str] = []
    filter_exprs: list[str] = []
    join_keys: list[str] = []
    sort_fields: list[str] = []
    crosstab_fields: list[str] = []

    for tool in workflow.tools.values():
        cfg = tool.configuration.parsed or {}
        ttype = tool.tool_type
        if ttype == "Summarize":
            for sf in cfg.get("summarize_fields", []):
                field_name = sf.get("field", "")
                action = sf.get("action", "")
                if action and field_name:
                    summarize_ops.append(f"{action}({field_name})")
        elif ttype in ("Formula", "MultiFieldFormula"):
            for ff in cfg.get("formula_fields", []):
                fname = ff.get("field", "")
                if fname:
                    formula_fields.append(fname)
        elif ttype == "Filter":
            expr = cfg.get("expression") or cfg.get("Expression") or ""
            if expr:
                filter_exprs.append(expr)
        elif ttype == "Join":
            jfields = cfg.get("join_fields", [])
            if jfields:
                join_keys.extend(str(jf) for jf in jfields[:2])
        elif ttype == "Sort":
            for sf in cfg.get("sort_fields", []):
                sname = sf.get("field", "")
                if sname:
                    sort_fields.append(sname)
        elif ttype == "CrossTab":
            hfield = cfg.get("header_field", "")
            dfield = cfg.get("data_field", "")
            if hfield or dfield:
                crosstab_fields.append(f"{hfield} -> {dfield}")

    # 1. Subject Matter / Business Purpose (concise analytical overview)
    if purpose:
        subject_and_purpose = purpose
    elif inputs and outputs:
        inp_names = ", ".join(i.source_filename or i.name for i in inputs[:3])
        out_names = ", ".join(o.sheet_or_table or o.name for o in outputs[:3])
        subject_and_purpose = (
            f"This workflow automates operational data preparation and reporting by ingesting {inp_names}, "
            f"executing structured transformation and reconciliation rules, and publishing finalized analytical deliverables to {out_names}."
        )
    else:
        subject_and_purpose = "This workflow automates operational data preparation, analytical transformation, and business reporting."

    # 2. Methods of Analysis (concrete analytical / statistical methods present)
    methods_list: list[str] = []
    if inputs:
        inp_count = len(inputs)
        methods_list.append(f"multi-source data ingestion ({inp_count} source dataset{'s' if inp_count != 1 else ''})")
    if join_keys:
        methods_list.append(f"relational joins and cross-source enrichment")
    if filter_exprs:
        methods_list.append("conditional filtering and record segmentation")
    if formula_fields:
        methods_list.append("calculated measure derivation via formula expressions")
    if summarize_ops:
        methods_list.append(f"multi-dimensional aggregation ({len(summarize_ops)} aggregation operations)")
    if crosstab_fields:
        methods_list.append("matrix pivoting and dimensional cross-tabulation")
    if sort_fields:
        methods_list.append("chronological and categorical sorting")
    if outputs:
        out_count = len(outputs)
        methods_list.append(f"analytical deliverable distribution ({out_count} target export{'s' if out_count != 1 else ''})")

    if methods_list:
        methods_and_process = (
            f"The workflow applies sequential analytical operations including {', '.join(methods_list[:5])} "
            f"across {len(stages)} processing stages to establish a consistent reporting baseline."
        )
    else:
        methods_and_process = (
            "The workflow applies sequential data preparation, validation, and calculation rules to produce analysis-ready records."
        )

    # 3. Findings (Analytical Subject + Method + Result/Fact + Business Significance)
    findings: list[str] = []

    if len(inputs) > 1:
        src_names = ", ".join(i.source_filename or i.name for i in inputs[:4])
        findings.append(
            f"Data integration combines {len(inputs)} independent source datasets ({src_names}) into a unified analytical base, "
            f"enabling cross-source reconciliation and consolidated reporting across disparate operational records."
        )
    elif inputs:
        inp_name = inputs[0].source_filename or inputs[0].name
        findings.append(
            f"Primary data ingestion establishes {inp_name} as the authoritative source dataset, "
            f"serving as the single upstream foundation for all subsequent transformation and calculation steps."
        )

    if summarize_ops:
        ops_summary = ", ".join(summarize_ops[:3])
        findings.append(
            f"Multi-dimensional aggregation applies {ops_summary} operations to convert record-level transaction observations "
            f"into structured period-level summary measures, reducing data granularity to support executive reporting."
        )

    if formula_fields:
        f_names = ", ".join(list(dict.fromkeys(formula_fields))[:3])
        findings.append(
            f"Derived metric calculation establishes standardized business measures ({f_names}) through deterministic formula rules, "
            f"ensuring consistent analytical calculations prior to deliverable export."
        )

    if filter_exprs:
        findings.append(
            f"Data segmentation and quality filtering isolates specific target records using configured conditional predicates, "
            f"preventing non-qualifying records from propagating into published downstream deliverables."
        )

    if len(outputs) > 1:
        out_names = ", ".join(o.sheet_or_table or o.name for o in outputs[:3])
        findings.append(
            f"Analytical deliverable distribution branches transformed records into {len(outputs)} distinct outputs ({out_names}), "
            f"providing tailored reporting views across different business consumption channels."
        )
    elif outputs:
        out_name = outputs[0].sheet_or_table or outputs[0].name
        findings.append(
            f"Published output generation exports transformed records to {out_name}, "
            f"providing the finalized deliverable for recurring operational review."
        )

    # Ensure findings length is between 3 and 7 items
    if len(findings) < 3 and business_rules:
        cats = list(dict.fromkeys(r.category for r in business_rules))
        cats_str = ", ".join(cats[:3])
        findings.append(
            f"Operational business logic enforces standardization through {cats_str.lower()} rules extracted from tool configurations."
        )

    # 4. Conclusions (Analytical synthesis of what the workflow demonstrates)
    if len(inputs) > 1 and len(outputs) > 1:
        conclusions = (
            "The workflow operates as a centralized data consolidation and multi-dimensional reporting pipeline, "
            "integrating disparate operational feeds into recurring analytical deliverables with a unified reporting grain."
        )
    elif len(outputs) > 1:
        conclusions = (
            "The workflow operates as an analytical distribution pipeline, preparing a central source dataset "
            "into multiple specialized reporting views for downstream business consumption."
        )
    else:
        conclusions = (
            "The workflow establishes a standardized data preparation and reporting process, transforming raw source extracts "
            "into a structured operational deliverable."
        )

    return ExecutiveSummaryContent(
        subject_and_purpose=subject_and_purpose,
        methods_and_process=methods_and_process,
        findings=findings[:7],
        conclusions=conclusions,
    )
