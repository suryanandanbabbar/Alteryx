"""Deterministic portfolio evidence aggregation, multi-signal similarity, and rationalisation analysis.

Enforces:
1. Multi-Signal Similarity (Constraint 1): Combines independent signals (tool sequence, graph topology,
   transformation signatures, source overlap, target overlap, field/lineage overlap).
2. Inspection Sink Distinction (Constraint 2): Distinguishes PRODUCTION_OUTPUT from Browse/BrowseV2 INSPECTION_SINK.
3. No Redundant LLM Re-runs (Constraint 3): Consumes existing cached results; never re-runs individual workflow LLMs.
4. Actual Filename Precedence & *Unknown Elimination: Purges wildcards and preserves physical configured file paths.
5. Strict Separation of Evidence from Interpretation: DeterministicSignals populated auditably.
"""

from __future__ import annotations

import difflib
import json
import logging
import uuid
from typing import Any

from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.portfolio import (
    BusinessAreaClassification,
    BusinessAreaGroup,
    DeterministicSignals,
    PortfolioAggregateMetrics,
    PortfolioAnalysis,
    PortfolioWorkflowSummary,
    RationalisationCandidate,
    SharedDataset,
    WorkflowRelationship,
)
from awa.analysis.sttm_extractor import _clean_table_name
from awa.analysis.business_area_classifier import (
    classify_workflow_business_area,
    classify_portfolio_business_areas,
    classify_business_area_deterministic,
    classify_business_function_deterministic,
    extract_output_evidence_for_workflow,
    BUSINESS_AREA_DESCRIPTIONS,
    ALLOWED_BUSINESS_AREAS,
)
from awa.analysis.workflow_complexity import calculate_workflow_complexity
from awa.analysis.workflow_criticality import (
    calculate_workflow_criticality,
    build_criticality_evidence_package,
    PortfolioDependencyContext,
)

logger = logging.getLogger(__name__)

ALL_PORTFOLIO_BUSINESS_AREAS: tuple[str, ...] = (
    "Claims & Risk",
    "Legal",
    "Underwriting",
    "Sales & Distribution",
    "Other / Unclassified",
)


def _get_cfg_dict(tool) -> dict:
    if not tool or not tool.configuration:
        return {}
    if hasattr(tool.configuration, "parsed") and isinstance(tool.configuration.parsed, dict):
        return tool.configuration.parsed
    if isinstance(tool.configuration, dict):
        return tool.configuration
    return {}


def _extract_workflow_sources(result: CanonicalAnalysisResult) -> list[str]:
    """Extract authoritative physical source dataset identities, preserving filename precedence."""
    sources: list[str] = []
    seen: set[str] = set()
    biz_inputs = {inp.tool_id: inp for inp in (result.business_summary.source_inputs if result.business_summary else [])}

    for tid, tool in sorted(result.workflow.tools.items()):
        is_input = (
            tool.tool_type in ("DbFileInput", "FileInput", "TextInput", "Directory", "DynamicInput")
            or (result.graph.has_node(tid) and result.graph.in_degree(tid) == 0)
        )
        if not is_input:
            continue

        cfg = _get_cfg_dict(tool)
        file_path = (
            cfg.get("file_path", "")
            or cfg.get("File", "")
            or cfg.get("source_file", "")
            or cfg.get("table_name", "")
        )

        name = ""
        if file_path:
            name = _clean_table_name(str(file_path))
        elif tid in biz_inputs and (biz_inputs[tid].source_filename or biz_inputs[tid].raw_source):
            raw = biz_inputs[tid].source_filename or biz_inputs[tid].raw_source
            if raw and raw.lower() not in ("in-memory configuration", "standard input stream"):
                name = _clean_table_name(raw)
            elif tool.tool_type == "TextInput":
                flds = cfg.get("fields", [])
                field_hint = f" ({', '.join(flds[:2])})" if flds else ""
                name = f"TextInput #{tid}{field_hint}"
            else:
                name = f"Source #{tid}"
        elif tool.tool_type == "TextInput":
            flds = cfg.get("fields", [])
            field_hint = f" ({', '.join(flds[:2])})" if flds else ""
            name = f"TextInput #{tid}{field_hint}"
        else:
            name = f"Source #{tid}"

        # Strictly purge *Unknown and wildcard tokens
        if not name or "*" in name or name.lower() == "*unknown":
            continue

        if name not in seen:
            seen.add(name)
            sources.append(name)

    return sources


def _extract_workflow_targets_and_sinks(
    result: CanonicalAnalysisResult,
) -> tuple[list[str], list[str], dict[str, str]]:
    """Extract production targets and inspection sinks separately per Constraint 2.

    Returns:
        (production_targets, inspection_sinks, sink_classifications)
    """
    production_targets: list[str] = []
    inspection_sinks: list[str] = []
    sink_classifications: dict[str, str] = {}
    seen_targets: set[str] = set()
    seen_sinks: set[str] = set()
    biz_outputs = {out.tool_id: out for out in (result.business_summary.business_outputs if result.business_summary else [])}

    for tid, tool in sorted(result.workflow.tools.items()):
        # 1. Inspection Sinks (Browse / BrowseV2)
        if tool.tool_type in ("BrowseV2", "Browse"):
            sink_name = f"Browse #{tid}"
            if sink_name not in seen_sinks:
                seen_sinks.add(sink_name)
                inspection_sinks.append(sink_name)
                sink_classifications[sink_name] = "INSPECTION_SINK"
            continue

        # 2. Production Sinks (DbFileOutput, OutputData, Render, or non-browse leaf)
        is_explicit_output = tool.tool_type in ("DbFileOutput", "OutputData", "Render")
        is_leaf = (
            result.graph.has_node(tid)
            and result.graph.out_degree(tid) == 0
            and tool.tool_type not in ("BrowseV2", "Browse")
        )

        if is_explicit_output or is_leaf:
            cfg = _get_cfg_dict(tool)
            file_path = (
                cfg.get("file_path", "")
                or cfg.get("File", "")
                or cfg.get("destination_file", "")
            )

            target_name = ""
            if file_path:
                target_name = _clean_table_name(str(file_path))
            elif tid in biz_outputs and (biz_outputs[tid].raw_destination or biz_outputs[tid].name):
                raw = biz_outputs[tid].raw_destination or biz_outputs[tid].name
                if raw and raw.lower() not in ("standard output stream", "in-memory destination"):
                    target_name = _clean_table_name(raw)
                else:
                    target_name = f"Deliverable #{tid}"
            elif is_explicit_output:
                target_name = f"Output #{tid}"
            else:
                target_name = f"Deliverable #{tid}"

            # Strictly purge *Unknown and wildcards
            if not target_name or "*" in target_name or target_name.lower() == "*unknown":
                continue

            if target_name not in seen_targets:
                seen_targets.add(target_name)
                production_targets.append(target_name)
                sink_classifications[target_name] = "PRODUCTION_OUTPUT"

    return production_targets, inspection_sinks, sink_classifications


def _calculate_tool_sequence_similarity(types_a: list[str], types_b: list[str]) -> float:
    """Calculate normalized sequence alignment similarity between two tool type sequences."""
    if not types_a or not types_b:
        return 0.0
    matcher = difflib.SequenceMatcher(None, types_a, types_b)
    return matcher.ratio()


def _calculate_graph_topology_similarity(res_a: CanonicalAnalysisResult, res_b: CanonicalAnalysisResult) -> float:
    """Calculate graph structural similarity (node/edge ratio, density, degree distributions)."""
    ga = res_a.graph
    gb = res_b.graph
    na, nb = ga.number_of_nodes(), gb.number_of_nodes()
    ea, eb = ga.number_of_edges(), gb.number_of_edges()

    if na == 0 and nb == 0:
        return 1.0
    if na == 0 or nb == 0:
        return 0.0

    node_ratio = min(na, nb) / max(na, nb)
    edge_ratio = min(ea + 1, eb + 1) / max(ea + 1, eb + 1)

    # In/Out degree distribution overlap
    in_deg_a = sorted([d for _, d in ga.in_degree()])
    in_deg_b = sorted([d for _, d in gb.in_degree()])
    deg_sim = difflib.SequenceMatcher(None, in_deg_a, in_deg_b).ratio()

    return 0.4 * node_ratio + 0.3 * edge_ratio + 0.3 * deg_sim


def _calculate_transformation_overlap(res_a: CanonicalAnalysisResult, res_b: CanonicalAnalysisResult) -> float:
    """Calculate overlap of transformation signatures (formulas, aggregations, joins, filters)."""
    transform_types = {"Filter", "Formula", "Join", "Summarize", "Union", "AlteryxSelect", "CrossTab", "Unique", "Sort"}
    set_a = {t.tool_type for t in res_a.workflow.tools.values() if t.tool_type in transform_types}
    set_b = {t.tool_type for t in res_b.workflow.tools.values() if t.tool_type in transform_types}

    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _calculate_field_and_lineage_overlap(
    res_a: CanonicalAnalysisResult,
    res_b: CanonicalAnalysisResult,
) -> tuple[float, float]:
    """Calculate field name overlap and STTM lineage (source_attr -> target_attr) overlap."""
    # Field overlap from input/output tools
    fields_a: set[str] = set()
    fields_b: set[str] = set()

    for tid, tool in res_a.workflow.tools.items():
        cfg = _get_cfg_dict(tool)
        if "select_fields" in cfg:
            sf_list = cfg.get("select_fields", [])
            for sf in sf_list:
                fld = sf.get("field") if isinstance(sf, dict) else str(sf)
                if fld and not fld.startswith("*"):
                    fields_a.add(fld)

    for tid, tool in res_b.workflow.tools.items():
        cfg = _get_cfg_dict(tool)
        if "select_fields" in cfg:
            sf_list = cfg.get("select_fields", [])
            for sf in sf_list:
                fld = sf.get("field") if isinstance(sf, dict) else str(sf)
                if fld and not fld.startswith("*"):
                    fields_b.add(fld)

    field_sim = 0.0
    if fields_a or fields_b:
        field_sim = len(fields_a & fields_b) / max(len(fields_a | fields_b), 1)

    # Lineage overlap from STTM
    pairs_a: set[tuple[str, str]] = set()
    pairs_b: set[tuple[str, str]] = set()

    if res_a.sttm:
        for m in res_a.sttm.mappings:
            if not m.source_attribute.startswith("*") and not m.target_attribute.startswith("*"):
                pairs_a.add((m.source_attribute, m.target_attribute))

    if res_b.sttm:
        for m in res_b.sttm.mappings:
            if not m.source_attribute.startswith("*") and not m.target_attribute.startswith("*"):
                pairs_b.add((m.source_attribute, m.target_attribute))

    lineage_sim = 0.0
    if pairs_a or pairs_b:
        lineage_sim = len(pairs_a & pairs_b) / max(len(pairs_a | pairs_b), 1)

    return field_sim, lineage_sim


def compute_multi_signal_relationship(
    wf_a: PortfolioWorkflowSummary,
    res_a: CanonicalAnalysisResult,
    wf_b: PortfolioWorkflowSummary,
    res_b: CanonicalAnalysisResult,
) -> WorkflowRelationship | None:
    """Compute auditable multi-signal relationship between two workflows per Constraint 1."""
    shared_srcs = sorted(list(set(wf_a.sources) & set(wf_b.sources)))
    shared_tgts = sorted(list(set(wf_a.targets) & set(wf_b.targets)))

    src_overlap = len(shared_srcs) / max(len(set(wf_a.sources) | set(wf_b.sources)), 1)
    tgt_overlap = len(shared_tgts) / max(len(set(wf_a.targets) | set(wf_b.targets)), 1) if (wf_a.targets or wf_b.targets) else 0.0

    tool_seq_sim = _calculate_tool_sequence_similarity(wf_a.tool_types, wf_b.tool_types)
    graph_sim = _calculate_graph_topology_similarity(res_a, res_b)
    transform_sim = _calculate_transformation_overlap(res_a, res_b)
    field_sim, lineage_sim = _calculate_field_and_lineage_overlap(res_a, res_b)

    composite = (
        0.25 * src_overlap
        + 0.25 * tgt_overlap
        + 0.15 * tool_seq_sim
        + 0.15 * graph_sim
        + 0.10 * transform_sim
        + 0.10 * max(field_sim, lineage_sim)
    )

    signals = DeterministicSignals(
        shared_sources=shared_srcs,
        shared_targets=shared_tgts,
        tool_sequence_similarity=tool_seq_sim,
        graph_topology_similarity=graph_sim,
        transformation_overlap=transform_sim,
        field_overlap=field_sim,
        lineage_overlap=lineage_sim,
        composite_score=composite,
    )

    # Classify relationship based on auditable evidence
    evidence: list[str] = []
    rel_type = "STRUCTURAL_SIMILARITY"
    confidence = "LOW"

    if shared_srcs:
        evidence.append(f"Shares {len(shared_srcs)} configured source dataset(s): {', '.join(shared_srcs)}")
    if shared_tgts:
        evidence.append(f"Shares {len(shared_tgts)} production deliverable(s): {', '.join(shared_tgts)}")
    if tool_seq_sim >= 0.65:
        evidence.append(f"{round(tool_seq_sim * 100)}% tool sequence alignment")
    if transform_sim >= 0.70:
        evidence.append(f"{round(transform_sim * 100)}% transformation signature overlap")
    if lineage_sim >= 0.50:
        evidence.append(f"{round(lineage_sim * 100)}% field lineage path match")

    # Decision tree for relationship classification
    if shared_srcs and shared_tgts and composite >= 0.70:
        rel_type = "DUPLICATE_CANDIDATE"
        confidence = "HIGH"
    elif shared_srcs and shared_tgts:
        rel_type = "OVERLAPPING_PIPELINE"
        confidence = "HIGH"
    elif shared_srcs and (transform_sim >= 0.6 or tool_seq_sim >= 0.6):
        rel_type = "SHARED_LOGIC"
        confidence = "MEDIUM" if composite >= 0.45 else "LOW"
    elif shared_srcs:
        rel_type = "SHARED_SOURCE"
        confidence = "HIGH"
    elif shared_tgts:
        rel_type = "SHARED_TARGET"
        confidence = "HIGH"
    elif composite >= 0.60:
        rel_type = "SEMANTIC_SIMILARITY"
        confidence = "MEDIUM"
    elif tool_seq_sim >= 0.60 or graph_sim >= 0.65:
        rel_type = "STRUCTURAL_SIMILARITY"
        confidence = "LOW"
    else:
        # Below significance threshold
        return None

    return WorkflowRelationship(
        workflow_a_id=wf_a.workflow_id,
        workflow_a_name=wf_a.filename,
        workflow_b_id=wf_b.workflow_id,
        workflow_b_name=wf_b.filename,
        relationship_type=rel_type,
        deterministic_signals=signals,
        llm_reasoning="",  # Populated strictly by qualification pass
        confidence=confidence,
        evidence=evidence,
    )


def build_portfolio_analysis(
    raw_workflows: list[tuple[str, str, CanonicalAnalysisResult | Exception]],
    portfolio_name: str = "ETL Portfolio",
    portfolio_id: str | None = None,
    generator: Any | None = None,
) -> PortfolioAnalysis:
    """Build authoritative PortfolioAnalysis from individual canonical workflow results.

    Arguments:
        raw_workflows: List of (filename, relative_path, CanonicalAnalysisResult | Exception)
        portfolio_name: Display name for the portfolio
        portfolio_id: Optional fixed portfolio ID; auto-generated if omitted.
        generator: Optional LLMNarrativeGenerator for semantic classification/enrichment.
    """
    pid = portfolio_id or f"portfolio_{uuid.uuid4().hex[:12]}"
    summaries: list[PortfolioWorkflowSummary] = []
    successful_results: dict[str, CanonicalAnalysisResult] = {}
    tool_counter: dict[str, int] = {}
    source_to_wfs: dict[str, list[tuple[str, str]]] = {}
    target_to_wfs: dict[str, list[tuple[str, str]]] = {}

    # 1. Process individual workflow outputs using canonical workflow business understanding
    for filename, rel_path, res_or_exc in raw_workflows:
        if isinstance(res_or_exc, Exception):
            # Record partial failure without failing entire portfolio
            summaries.append(
                PortfolioWorkflowSummary(
                    workflow_id=f"failed_{uuid.uuid4().hex[:8]}",
                    filename=filename,
                    relative_path=rel_path,
                    status="FAILED",
                    error_message=str(res_or_exc),
                )
            )
            continue

        res = res_or_exc
        wid = res.analysis_id
        successful_results[wid] = res

        srcs = _extract_workflow_sources(res)
        tgts, sinks, classifications = _extract_workflow_targets_and_sinks(res)

        tool_seq = [res.workflow.tools[t].tool_type for t in res.execution_order if t in res.workflow.tools]
        for ttype in tool_seq:
            tool_counter[ttype] = tool_counter.get(ttype, 0) + 1

        for s in srcs:
            source_to_wfs.setdefault(s, []).append((wid, filename))
        for t in tgts:
            target_to_wfs.setdefault(t, []).append((wid, filename))

        raw_purpose = getattr(res, "business_purpose", "")
        biz_purpose = raw_purpose if isinstance(raw_purpose, str) else ""
        raw_func = getattr(res, "business_function", "")
        biz_func = raw_func if isinstance(raw_func, str) else ""
        raw_tax_ver = getattr(res, "business_area_taxonomy_version", "3.0")
        tax_ver = raw_tax_ver if isinstance(raw_tax_ver, str) else "3.0"
        raw_conflict = getattr(res, "classification_conflict", False)
        conflict = bool(raw_conflict)
        sttm_count = len(res.sttm.mappings) if res.sttm else 0

        # Read canonical upload-time business-area tag (no secondary portfolio LLM classification)
        raw_tag = getattr(res, "business_area_tag", "")
        tag = raw_tag.strip() if isinstance(raw_tag, str) else ""
        raw_source = getattr(res, "business_area_tag_source", "")
        tag_source = raw_source if isinstance(raw_source, str) else "deterministic_fallback"

        valid_buckets = set(ALLOWED_BUSINESS_AREAS) | {"Other / Unclassified"}

        # Only run deterministic fallback when canonical tag is missing, empty, UNCLASSIFIED, or invalid
        if not tag or tag == "UNCLASSIFIED" or tag not in valid_buckets:
            out_ev = extract_output_evidence_for_workflow(res)
            input_srcs = srcs
            det = classify_business_area_deterministic(
                out_ev,
                business_purpose=biz_purpose,
                workflow_name=filename,
                business_function=biz_func,
                input_sources=input_srcs,
            )
            tag = det.business_area if det.business_area in valid_buckets else "Other / Unclassified"
            tag_source = "deterministic_fallback"
            if not biz_func:
                biz_func = classify_business_function_deterministic(
                    tag, workflow_name=filename, business_purpose=biz_purpose
                )

        # Ensure canonical tag is strictly one of the 5 allowed buckets
        if tag not in valid_buckets:
            tag = "Other / Unclassified"

        # Keep canonical result business summary in sync if missing
        if hasattr(res, "business_summary") and res.business_summary:
            if getattr(res.business_summary, "business_area_tag", None) in (None, "", "UNCLASSIFIED"):
                res.business_summary.business_area_tag = tag
            if not getattr(res.business_summary, "business_function", None) and biz_func:
                res.business_summary.business_function = biz_func

        classification = BusinessAreaClassification(
            business_area=tag,
            confidence="HIGH" if tag_source == "llm" else "MEDIUM",
            evidence=[biz_purpose[:120]] if biz_purpose else [],
            classification_source=tag_source,
            secondary_business_areas=[],
            classification_conflict=conflict,
            business_area_taxonomy_version=tax_ver,
        )

        # Deterministic Workflow Complexity Assessment
        complexity = calculate_workflow_complexity(res)

        summaries.append(
            PortfolioWorkflowSummary(
                workflow_id=wid,
                analysis_id=wid,
                filename=filename,
                relative_path=rel_path,
                status="SUCCESS",
                node_count=len(res.workflow.tools),
                connection_count=res.metrics.total_connections if res.metrics else len(res.workflow.connections),
                source_count=len(srcs),
                target_count=len(tgts),
                sources=srcs,
                targets=tgts,
                inspection_sinks=sinks,
                sink_classifications=classifications,
                tool_types=tool_seq,
                business_purpose=biz_purpose,
                business_function=biz_func,
                sttm_mappings_count=sttm_count,
                business_area=classification,
                business_area_tag=tag,
                business_area_tag_source=tag_source,
                business_area_taxonomy_version=tax_ver,
                complexity_score=complexity.score,
                complexity_level=complexity.level,
                complexity_factors=complexity.factors,
            )
        )

    # 2. Identify shared datasets across multiple workflows
    shared_sources: list[SharedDataset] = [
        SharedDataset(
            dataset_name=sname,
            dataset_type="SOURCE",
            workflow_ids=[item[0] for item in items],
            workflow_names=[item[1] for item in items],
        )
        for sname, items in sorted(source_to_wfs.items())
        if len(items) >= 2
    ]

    shared_targets: list[SharedDataset] = [
        SharedDataset(
            dataset_name=tname,
            dataset_type="TARGET",
            workflow_ids=[item[0] for item in items],
            workflow_names=[item[1] for item in items],
        )
        for tname, items in sorted(target_to_wfs.items())
        if len(items) >= 2
    ]

    # 2b. Deterministic Workflow Criticality Assessment (using portfolio dependency context)
    dep_context = PortfolioDependencyContext(
        target_to_producers={t: [(w, f) for w, f in items] for t, items in target_to_wfs.items()},
        source_to_consumers={s: [(w, f) for w, f in items] for s, items in source_to_wfs.items()},
        shared_targets={s.dataset_name for s in shared_targets},
        shared_sources={s.dataset_name for s in shared_sources},
    )

    from awa.llm.generator import compose_deterministic_criticality_fallback

    for wf in summaries:
        if wf.status == "SUCCESS":
            res = successful_results.get(wf.workflow_id)
            bs = getattr(res, "business_summary", None)

            # Check if workflow already has an assessed criticality from canonical upload-time analysis
            raw_score = getattr(bs, "criticality_score", None)
            has_canonical_crit = (
                bs is not None
                and isinstance(raw_score, (int, float))
            )
            has_new_portfolio_deps = bool(
                (wf.targets and any(len(dep_context.source_to_consumers.get(t, [])) > 0 for t in wf.targets))
                or (wf.sources and any(len(dep_context.target_to_producers.get(s, [])) > 0 for s in wf.sources))
            )

            if has_canonical_crit and not has_new_portfolio_deps:
                wf.criticality_score = float(raw_score)
                wf.criticality_level = getattr(bs, "criticality_level", "LOW")
                wf.criticality_factors = getattr(bs, "criticality_factors", None) or []
                wf.criticality_justification = getattr(bs, "criticality_justification", "")
                wf.criticality_business_consequence = getattr(bs, "criticality_business_consequence", "")
                wf.criticality_dependency_impact = getattr(bs, "criticality_dependency_impact", "")
                wf.criticality_affected_scope = getattr(bs, "criticality_affected_scope", "")
                wf.criticality_migration_implication = getattr(bs, "criticality_migration_implication", "")
                wf.criticality_confidence = getattr(bs, "criticality_confidence", "HIGH")
                wf.criticality_source = getattr(bs, "criticality_source", "llm")
                wf.factor_assessments = getattr(bs, "factor_assessments", {})
            else:
                ev = build_criticality_evidence_package(
                    workflow_id=wf.workflow_id,
                    workflow_filename=wf.filename,
                    sources=wf.sources,
                    targets=wf.targets,
                    inspection_sinks=wf.inspection_sinks,
                    context=dep_context,
                    business_purpose=wf.business_purpose,
                    business_function=wf.business_function,
                    business_area=wf.business_area_tag,
                    deterministic_counts={
                        "total_nodes": wf.node_count,
                        "total_connections": wf.connection_count,
                        "source_count": wf.source_count,
                        "target_count": wf.target_count,
                        "inspection_sink_count": len(wf.inspection_sinks),
                        "downstream_consumer_count": len(dep_context.source_to_consumers.get(wf.targets[0], [])) if wf.targets else 0,
                    },
                )
                # Single canonical LLM generation owner is canonical upload analysis;
                # portfolio aggregation strictly uses deterministic fallback when evaluating new cross-workflow context.
                crit_res = compose_deterministic_criticality_fallback(ev)
                wf.criticality_score = crit_res.criticality_score
                wf.criticality_level = crit_res.criticality_level
                wf.criticality_factors = crit_res.criticality_factors
                wf.criticality_justification = crit_res.criticality_justification
                wf.criticality_business_consequence = crit_res.business_consequence
                wf.criticality_dependency_impact = crit_res.dependency_impact
                wf.criticality_affected_scope = crit_res.affected_scope
                wf.criticality_migration_implication = crit_res.migration_implication
                wf.criticality_confidence = crit_res.confidence
                wf.criticality_source = crit_res.source
                wf.factor_assessments = {
                    k: v.to_dict() if hasattr(v, "to_dict") else v
                    for k, v in crit_res.factor_assessments.items()
                }

    # 3. Compute Multi-Signal Relationships between all pairs of successful workflows
    relationships: list[WorkflowRelationship] = []
    success_summaries = [s for s in summaries if s.status == "SUCCESS"]

    for i in range(len(success_summaries)):
        for j in range(i + 1, len(success_summaries)):
            wf_a = success_summaries[i]
            wf_b = success_summaries[j]
            res_a = successful_results.get(wf_a.workflow_id)
            res_b = successful_results.get(wf_b.workflow_id)
            if not res_a or not res_b:
                continue

            rel = compute_multi_signal_relationship(wf_a, res_a, wf_b, res_b)
            if rel is not None:
                relationships.append(rel)

    # 4. Derive initial deterministic rationalisation candidates
    candidates: list[RationalisationCandidate] = []
    for rel in relationships:
        if rel.relationship_type == "DUPLICATE_CANDIDATE":
            candidates.append(
                RationalisationCandidate(
                    workflow_ids=[rel.workflow_a_id, rel.workflow_b_id],
                    workflow_names=[rel.workflow_a_name, rel.workflow_b_name],
                    recommendation_type="CONSOLIDATE",
                    reasoning=f"Identified as candidate duplicate workflows with high composite similarity ({rel.deterministic_signals.composite_score}) and identical source/target datasets.",
                    evidence=rel.evidence,
                    confidence=rel.confidence,
                )
            )
        elif rel.relationship_type in ("OVERLAPPING_PIPELINE", "SHARED_LOGIC") and rel.confidence in ("HIGH", "MEDIUM"):
            candidates.append(
                RationalisationCandidate(
                    workflow_ids=[rel.workflow_a_id, rel.workflow_b_id],
                    workflow_names=[rel.workflow_a_name, rel.workflow_b_name],
                    recommendation_type="SHARED_LOGIC",
                    reasoning=f"Workflows share common operational logic ({round(rel.deterministic_signals.transformation_overlap * 100)}% transformation overlap) and data assets.",
                    evidence=rel.evidence,
                    confidence=rel.confidence,
                )
            )

    # Check for workflows with 0 production targets and inspection sinks only
    for wf in success_summaries:
        if wf.target_count == 0 and len(wf.inspection_sinks) > 0:
            candidates.append(
                RationalisationCandidate(
                    workflow_ids=[wf.workflow_id],
                    workflow_names=[wf.filename],
                    recommendation_type="REVIEW",
                    reasoning=f"Workflow produces no production deliverables and terminates only in inspection sink(s) ({', '.join(wf.inspection_sinks)}). Potential development or inspection asset.",
                    evidence=[f"Terminal inspection sinks: {', '.join(wf.inspection_sinks)}", "Zero production deliverables configured"],
                    confidence="HIGH",
                )
            )

    # 5. Aggregate metrics
    metrics = PortfolioAggregateMetrics(
        total_workflows=len(summaries),
        successful_workflows=len(success_summaries),
        failed_workflows=len(summaries) - len(success_summaries),
        total_tools=sum(s.node_count for s in success_summaries),
        total_sources=sum(s.source_count for s in success_summaries),
        unique_sources=len(source_to_wfs),
        total_targets=sum(s.target_count for s in success_summaries),
        unique_targets=len(target_to_wfs),
        shared_sources_count=len(shared_sources),
        shared_targets_count=len(shared_targets),
        inspection_sinks_count=sum(len(s.inspection_sinks) for s in success_summaries),
        tool_distribution=tool_counter,
    )

    # 6. Aggregate business areas and materialise ALL 5 configured business areas
    ALL_PORTFOLIO_BUSINESS_AREAS = (
        "Claims & Risk",
        "Legal",
        "Underwriting",
        "Sales & Distribution",
        "Other / Unclassified",
    )
    workflows_by_area: dict[str, list[PortfolioWorkflowSummary]] = {
        area: [] for area in ALL_PORTFOLIO_BUSINESS_AREAS
    }

    for s in success_summaries:
        tag = s.business_area_tag if s.business_area_tag in workflows_by_area else "Other / Unclassified"
        workflows_by_area[tag].append(s)

    # Materialise EVERY configured business area (even with 0 workflows)
    area_counts: dict[str, int] = {}
    business_area_groups: list[BusinessAreaGroup] = []

    for area in ALL_PORTFOLIO_BUSINESS_AREAS:
        wfs = workflows_by_area[area]
        area_counts[area] = len(wfs)
        business_area_groups.append(
            BusinessAreaGroup(
                business_area=area,
                workflow_count=len(wfs),
                workflows=wfs,
                description=BUSINESS_AREA_DESCRIPTIONS.get(area, ""),
            )
        )

    total_wf = len(summaries)
    attempted_wf = len(success_summaries)
    structured_success = sum(1 for s in success_summaries if s.business_area_tag_source == "llm")
    fallback_count = sum(1 for s in success_summaries if s.business_area_tag_source != "llm")
    conflict_count = sum(1 for s in success_summaries if getattr(s.business_area, "classification_conflict", False))
    unclassified_count = len(workflows_by_area["Other / Unclassified"])
    valid_tags_count = total_wf - unclassified_count
    criticality_impacted = sum(
        1 for s in success_summaries
        if isinstance(getattr(s, "criticality_score", None), (int, float))
        and getattr(s, "criticality_score", 0.0) > 0
        and getattr(s, "business_purpose", "")
    )

    logger.info(
        "[PORTFOLIO OBSERVABILITY] workflows=%d attempted=%d structured_success=%d "
        "valid_tags=%d fallbacks=%d conflicts=%d unclassified=%d criticality_impacted=%d",
        total_wf,
        attempted_wf,
        structured_success,
        valid_tags_count,
        fallback_count,
        conflict_count,
        unclassified_count,
        criticality_impacted,
    )

    return PortfolioAnalysis(
        portfolio_id=pid,
        portfolio_name=portfolio_name,
        workflow_count=len(summaries),
        workflows=summaries,
        metrics=metrics,
        shared_sources=shared_sources,
        shared_targets=shared_targets,
        relationships=relationships,
        rationalisation_candidates=candidates,
        business_area_counts=area_counts,
        business_area_descriptions=dict(BUSINESS_AREA_DESCRIPTIONS),
        business_areas=business_area_groups,
    )


def enrich_portfolio_with_llm(portfolio: PortfolioAnalysis) -> PortfolioAnalysis:
    """Semantically qualify candidate relationships and rationalisation opportunities using LLM.

    Strict Invariants:
    1. Reuses existing LLM client, cache, and prompt infrastructure.
    2. Consumes compact structured evidence only — never raw XML or full reports.
    3. Cannot invent workflows, datasets, fields, or relationships (hallucination guard).
    4. Deterministic fallback on client failure, timeout, or malformed JSON.
    """
    if portfolio.metrics.successful_workflows < 2:
        return portfolio

    # If no candidate relationships or rationalisation candidates, nothing for LLM to qualify
    if not portfolio.relationships and not portfolio.rationalisation_candidates:
        return portfolio

    from awa.llm import get_default_generator
    from awa.llm.cache import compute_cache_key, NarrativeResult
    from awa.llm.prompts import (
        PORTFOLIO_RATIONALISATION_PROMPT_VERSION,
        PORTFOLIO_RATIONALISATION_SYSTEM_PROMPT,
        build_portfolio_rationalisation_user_prompt,
    )

    generator = get_default_generator()
    if not generator.client.is_available:
        logger.info("[Portfolio LLM] LLM client unavailable/disabled — preserving deterministic facts.")
        return portfolio

    # 1. Build compact structured evidence payload
    valid_wf_ids = {w.workflow_id for w in portfolio.workflows if w.status == "SUCCESS"}
    evidence_payload = {
        "portfolio_name": portfolio.portfolio_name,
        "workflow_count": portfolio.metrics.successful_workflows,
        "workflows": [
            {
                "id": w.workflow_id,
                "name": w.filename,
                "sources": w.sources,
                "targets": w.targets,
                "inspection_sinks": w.inspection_sinks,
                "business_purpose": w.business_purpose[:250] if w.business_purpose else "",
                "tool_count": w.node_count,
            }
            for w in portfolio.workflows
            if w.status == "SUCCESS"
        ],
        "shared_sources": [s.to_dict() for s in portfolio.shared_sources],
        "shared_targets": [t.to_dict() for t in portfolio.shared_targets],
        "candidate_relationships": [
            {
                "workflow_a_id": r.workflow_a_id,
                "workflow_a_name": r.workflow_a_name,
                "workflow_b_id": r.workflow_b_id,
                "workflow_b_name": r.workflow_b_name,
                "relationship_type": r.relationship_type,
                "signals": r.deterministic_signals.to_dict(),
                "evidence": r.evidence,
            }
            for r in portfolio.relationships
        ],
        "candidate_recommendations": [c.to_dict() for c in portfolio.rationalisation_candidates],
    }

    cache_key = compute_cache_key(
        workflow_id=portfolio.portfolio_id,
        scope_key="portfolio_rationalisation",
        prompt_version=PORTFOLIO_RATIONALISATION_PROMPT_VERSION,
        model_name=generator.client.model_name,
        facts_payload=evidence_payload,
    )

    raw_response: str | None = None
    cached = generator._cache.get(cache_key)
    if cached is not None:
        logger.info("[Portfolio LLM CACHE] status=HIT")
        raw_response = cached.text
    else:
        logger.info("[Portfolio LLM CACHE] status=MISS")
        system_prompt = PORTFOLIO_RATIONALISATION_SYSTEM_PROMPT
        user_prompt = build_portfolio_rationalisation_user_prompt(evidence_payload)
        try:
            raw_response = generator.client.generate(system_prompt, user_prompt, max_tokens=2500)
        except Exception as e:
            logger.warning("[Portfolio LLM] Client error: %s — using deterministic baseline.", e)
            return portfolio

    if not raw_response or not raw_response.strip():
        return portfolio

    # Parse and validate JSON response
    try:
        clean_text = raw_response.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[-1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()
        parsed = json.loads(clean_text)
    except Exception as e:
        logger.warning("[Portfolio LLM] Failed to parse response JSON: %s", e)
        return portfolio

    # 2. Reconcile qualified relationships
    rel_lookup = {
        (r.workflow_a_id, r.workflow_b_id): r for r in portfolio.relationships
    }
    # Also index reverse
    for r in portfolio.relationships:
        rel_lookup[(r.workflow_b_id, r.workflow_a_id)] = r

    for q_rel in parsed.get("qualified_relationships", []):
        wa_id = q_rel.get("workflow_a_id")
        wb_id = q_rel.get("workflow_b_id")
        reasoning = q_rel.get("reasoning")

        # Invariant 16: Guard against hallucinated workflow IDs
        if wa_id not in valid_wf_ids or wb_id not in valid_wf_ids:
            logger.warning("[Portfolio LLM] Discarded hallucinated relationship: %s <-> %s", wa_id, wb_id)
            continue

        pair_key = (wa_id, wb_id)
        if pair_key in rel_lookup and reasoning:
            rel = rel_lookup[pair_key]
            rel.llm_reasoning = reasoning.strip()
            conf = q_rel.get("confidence")
            if conf in ("HIGH", "MEDIUM", "LOW"):
                rel.confidence = conf

    # 3. Reconcile recommendations
    llm_recommendations = parsed.get("rationalisation_recommendations", [])
    for rec in llm_recommendations:
        rec_wf_ids = rec.get("workflow_ids", [])
        rec_type = rec.get("recommendation_type")
        reasoning = rec.get("reasoning")
        conf = rec.get("confidence", "MEDIUM")

        # Guard: all referenced workflow IDs must exist
        if not all(wid in valid_wf_ids for wid in rec_wf_ids):
            logger.warning("[Portfolio LLM] Discarded hallucinated recommendation with invalid IDs: %s", rec_wf_ids)
            continue

        if not rec_wf_ids or not reasoning:
            continue

        # Check if already present in candidates
        matched_cand = None
        for cand in portfolio.rationalisation_candidates:
            if set(cand.workflow_ids) == set(rec_wf_ids):
                matched_cand = cand
                break

        if matched_cand:
            matched_cand.reasoning = reasoning.strip()
            if rec_type in ("CONSOLIDATE", "RETIRE_CANDIDATE", "SHARED_LOGIC", "REVIEW"):
                matched_cand.recommendation_type = rec_type
            if conf in ("HIGH", "MEDIUM", "LOW"):
                matched_cand.confidence = conf
        else:
            cand_names = [w.filename for w in portfolio.workflows if w.workflow_id in rec_wf_ids]
            portfolio.rationalisation_candidates.append(
                RationalisationCandidate(
                    workflow_ids=rec_wf_ids,
                    workflow_names=cand_names,
                    recommendation_type=rec_type if rec_type in ("CONSOLIDATE", "RETIRE_CANDIDATE", "SHARED_LOGIC", "REVIEW") else "REVIEW",
                    reasoning=reasoning.strip(),
                    evidence=[f"Identified through semantic qualification across {len(rec_wf_ids)} workflows"],
                    confidence=conf if conf in ("HIGH", "MEDIUM", "LOW") else "MEDIUM",
                )
            )

    # 4. Cache valid LLM response
    generator._cache.set(
        cache_key,
        NarrativeResult(
            text=raw_response,
            source="llm",
            model=generator.client.model_name,
            prompt_version=PORTFOLIO_RATIONALISATION_PROMPT_VERSION,
        ),
    )

    return portfolio

