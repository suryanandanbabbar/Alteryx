"""Deterministic ETL Rationalisation Analyzer.

Follows strict architectural hierarchy:
Canonical Workflow Analysis Result
      ↓
Deterministic Workflow Fingerprint
      ↓
Cross-Workflow Comparison & Similarity Metrics
      ↓
Deterministic Candidate Detection & Safety Gates
      ↓
Admissible Recommendation Set
      ↓
Existing LLM Infrastructure (Optional Semantic Interpretation)
      ↓
Deterministic Validation Layer
      ↓
Final Explainable Rationalisation Recommendation
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.portfolio import (
    DependencyEvidence,
    DeterministicMetrics,
    OutputEvidence,
    PortfolioAnalysis,
    PortfolioWorkflowSummary,
    RationalisationAnalysis,
    RationalisationCandidate,
    RiskContext,
    WorkflowComparisonEvidence,
    WorkflowFingerprint,
)
from awa.llm.cache import compute_cache_key
from awa.llm.generator import LLMNarrativeGenerator, get_default_generator
from awa.llm.schemas import NarrativeResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configurable Rationalisation Thresholds (Named Constants)
# ---------------------------------------------------------------------------
class RationalisationThresholds:
    """Configurable evidence boundaries for candidate classification."""
    # Retirement safety gates (strict: requires high target and logic match, compatible schema and grain)
    RETIRE_TARGET_OVERLAP_MIN: float = 0.85
    RETIRE_LOGIC_SIMILARITY_MIN: float = 0.75
    RETIRE_SCHEMA_SIMILARITY_MIN: float = 0.75
    RETIRE_MAX_UNIQUE_LOGIC_COUNT: int = 1

    # Consolidation boundaries
    CONSOLIDATE_SOURCE_OVERLAP_MIN: float = 0.50
    CONSOLIDATE_LOGIC_SIMILARITY_MIN: float = 0.45
    CONSOLIDATE_MIN_OPPORTUNITY_SCORE: float = 40.0

    # Shared logic boundaries
    SHARED_LOGIC_SIMILARITY_MIN: float = 0.35

    # Review boundaries
    REVIEW_OVERLAP_MIN: float = 0.25

    # Minimum opportunity score to surface as a rationalisation candidate (NO_ACTION suppressed)
    MIN_SURFACE_SCORE: float = 25.0


# ---------------------------------------------------------------------------
# 1. Deterministic Workflow Fingerprinting
# ---------------------------------------------------------------------------
def normalize_name(name: str) -> str:
    """Normalize file or dataset name for deterministic matching."""
    if not name:
        return ""
    clean = Path(name).name.strip().lower()
    # Remove file extension and extraneous symbols
    clean = re.sub(r"\.(xlsx|xls|csv|yxdb|tde|hyper|avro|parquet|json)$", "", clean)
    clean = re.sub(r"[^a-z0-9_]", "_", clean)
    return re.sub(r"_+", "_", clean).strip("_")


def normalize_expression(expr: str) -> str:
    """Normalize formula or filter expression for structural comparison."""
    if not expr:
        return ""
    norm = expr.strip().lower()
    norm = re.sub(r"\s+", " ", norm)
    norm = norm.replace('"', "'")
    return norm


DISALLOWED_EVIDENCE_TOKENS: tuple[str, ...] = (
    "=",
    ":",
    "=:",
    ":=",
    "join on =",
    "join on :",
    "join on:",
    "join on",
    "shared join key: =",
    "shared join key:",
    "shared join key",
    "formula: =",
    "formula:",
    "filter: =",
    "filter:",
    "summarize: =",
    "summarize:",
    "summarize aggregations",
    "aggregation: =",
    "aggregation:",
    "target: =",
    "target:",
)

GENERIC_TOOL_MARKERS: tuple[str, ...] = (
    "join operation",
    "filter operation",
    "summarize aggregations",
    "summarize operation",
    "formula calculation",
    "multirowformula calculation",
)


def is_meaningful_evidence(item: str | None) -> bool:
    """Determine whether an evidence string represents concrete, valid operational logic.

    Rejects:
    - None, empty, or whitespace-only strings
    - Synthetic/placeholder tokens: '=', ':', 'Join on =', 'Shared join key: ='
    - Label-only prefixes without values: 'Join on:', 'Formula:', 'Filter:'
    - Generic tool-presence markers: 'Join operation', 'Filter operation'
    """
    if not item or not isinstance(item, str):
        return False
    clean = item.strip()
    if not clean:
        return False
    lower = clean.lower()
    if lower in DISALLOWED_EVIDENCE_TOKENS or lower in GENERIC_TOOL_MARKERS:
        return False
    # Check prefixes with empty or synthetic values
    for prefix in (
        "shared join key:",
        "shared join key",
        "join on:",
        "join on",
        "formula:",
        "formula",
        "filter:",
        "filter",
        "shared filter predicate:",
        "summarize:",
        "summarize aggregations",
        "aggregation:",
        "target:",
    ):
        if lower.startswith(prefix):
            val = clean[len(prefix):].strip()
            if not val or val in ("=", ":", "=:", ":=") or val.replace("=", "").replace(":", "").strip() == "":
                return False
            if val.lower() in ("operation", "calculation", "aggregations"):
                return False
    return True


def format_summarize_fields(summarize_fields: list[dict[str, Any]]) -> str:
    """Format structured Summarize fields with stable ordering (GroupBy first, then aggregates)."""
    group_bys: list[str] = []
    aggregates: list[str] = []
    for sf in summarize_fields:
        if not isinstance(sf, dict):
            continue
        field = str(sf.get("field") or "").strip()
        action = str(sf.get("action") or "").strip()
        rename = str(sf.get("rename") or "").strip()
        if not field and not action:
            continue
        if action.lower() == "groupby":
            group_bys.append(f"GroupBy({field})")
        else:
            if rename and rename.lower() != field.lower():
                aggregates.append(f"{action}({field}) as {rename}")
            else:
                aggregates.append(f"{action}({field})")

    group_bys.sort()
    aggregates.sort()
    ordered = group_bys + aggregates
    return ", ".join(ordered)


def build_workflow_fingerprint(
    summary: PortfolioWorkflowSummary,
    canonical_res: CanonicalAnalysisResult,
    downstream_consumers: Optional[list[str]] = None,
) -> WorkflowFingerprint:
    """Build a deterministic, reproducible fingerprint from canonical workflow analysis."""
    wf = canonical_res.workflow
    dag = getattr(canonical_res, "dag", None)

    # 1. Sources (strictly exclude *Unknown and empty)
    clean_sources: list[str] = []
    source_types: dict[str, str] = {}
    source_fields: dict[str, list[str]] = {}
    for s in summary.sources:
        if not s or s == "*Unknown" or "unknown" in s.lower():
            continue
        norm_s = normalize_name(s)
        if norm_s and norm_s not in clean_sources:
            clean_sources.append(norm_s)
            source_types[norm_s] = "FILE"

    # Discover source fields if present in canonical result
    lineage_attr = getattr(canonical_res, "lineage", None)
    if lineage_attr and hasattr(lineage_attr, "source_fields"):
        for src, fields in lineage_attr.source_fields.items():
            norm_src = normalize_name(src)
            clean_flds = [getattr(f, "name", str(f)) for f in fields if getattr(f, "name", str(f)) and getattr(f, "name", str(f)) != "*Unknown"]
            if clean_flds:
                source_fields[norm_src] = sorted(clean_flds)

    # 2. Production Targets vs Inspection Sinks
    clean_targets: list[str] = []
    for t in summary.targets:
        if not t or t == "*Unknown" or "unknown" in t.lower():
            continue
        norm_t = normalize_name(t)
        if norm_t and norm_t not in clean_targets:
            clean_targets.append(norm_t)

    clean_sinks = [normalize_name(s) for s in summary.inspection_sinks if s]

    # Output schemas & fields from STTM, lineage_paths, or output_schema
    output_schemas: dict[str, list[str]] = {}
    schema_attr = getattr(canonical_res, "output_schema", None)
    if schema_attr and hasattr(schema_attr, "fields"):
        fnames = [getattr(f, "name", str(f)) for f in schema_attr.fields if getattr(f, "name", str(f)) and getattr(f, "name", str(f)) != "*Unknown"]
        for t in clean_targets:
            output_schemas[t] = sorted(list(set(fnames)))

    sttm_doc = getattr(canonical_res, "sttm", None)
    if sttm_doc and hasattr(sttm_doc, "mappings") and isinstance(sttm_doc.mappings, list):
        for m in sttm_doc.mappings:
            src_fld = getattr(m, "source_field", "")
            tgt_fld = getattr(m, "target_field", "")
            if src_fld and src_fld != "*Unknown":
                source_fields.setdefault("sources", []).append(src_fld)
            if tgt_fld and tgt_fld != "*Unknown":
                for t in clean_targets:
                    output_schemas.setdefault(t, []).append(tgt_fld)

    lineage_paths = getattr(canonical_res, "lineage_paths", None)
    if lineage_paths and isinstance(lineage_paths, list):
        for lp in lineage_paths:
            src_fld = getattr(lp, "source_field", "")
            tgt_fld = getattr(lp, "target_field", "")
            if src_fld and src_fld != "*Unknown":
                source_fields.setdefault("sources", []).append(src_fld)
            if tgt_fld and tgt_fld != "*Unknown":
                for t in clean_targets:
                    output_schemas.setdefault(t, []).append(tgt_fld)

    for k, v in output_schemas.items():
        output_schemas[k] = sorted(list(set(v)))
    for k, v in source_fields.items():
        source_fields[k] = sorted(list(set(v)))

    # 3. Output Grain Determination
    output_grain: list[str] = []
    for tool in wf.tools.values():
        if tool.tool_type == "Summarize" and tool.configuration:
            cfg_xml = tool.configuration.raw_xml if hasattr(tool.configuration, "raw_xml") else ""
            if "action=\"groupby\"" in cfg_xml.lower():
                matches = re.findall(r'field=["\']([^"\']+)["\']\s+action=["\']GroupBy["\']', cfg_xml, re.IGNORECASE)
                for m in matches:
                    if m and m not in output_grain and m != "*Unknown":
                        output_grain.append(m.lower())

    if not output_grain:
        output_grain = ["UNKNOWN"]

    # 4. Transformations
    tool_types = sorted(list({t.tool_type for t in wf.tools.values()}))
    transformation_signatures: list[str] = []
    filters: list[str] = []
    join_keys: list[str] = []
    aggregations: list[str] = []
    formulas: list[str] = []
    has_python = False
    has_r = False
    has_macros = False

    for tool in wf.tools.values():
        ttype = tool.tool_type
        cfg = tool.configuration
        parsed_dict = cfg.parsed if (cfg and hasattr(cfg, "parsed") and isinstance(cfg.parsed, dict)) else {}
        raw_xml_str = cfg.raw_xml if (cfg and hasattr(cfg, "raw_xml") and isinstance(cfg.raw_xml, str)) else ""

        if ttype == "Filter":
            expr = str(parsed_dict.get("expression", "") or "")
            if not expr and "<expression>" in raw_xml_str.lower():
                m_exp = re.search(r"<Expression[^>]*>(.*?)</Expression>", raw_xml_str, re.DOTALL | re.IGNORECASE)
                if m_exp:
                    expr = m_exp.group(1).strip()
            if expr:
                norm_expr = normalize_expression(expr)
                filters.append(norm_expr)
                transformation_signatures.append(f"Filter: {norm_expr}")
            else:
                transformation_signatures.append("Filter operation")

        elif ttype == "Join":
            join_fields = getattr(cfg, "join_fields", []) or parsed_dict.get("join_fields", []) or []
            jk = []
            if join_fields:
                for jf in join_fields:
                    left = ""
                    right = ""
                    if isinstance(jf, dict):
                        left = str(jf.get("left") or jf.get("left_field") or "").strip()
                        right = str(jf.get("right") or jf.get("right_field") or "").strip()
                    elif hasattr(jf, "left") or hasattr(jf, "left_field"):
                        left = str(getattr(jf, "left", "") or getattr(jf, "left_field", "")).strip()
                        right = str(getattr(jf, "right", "") or getattr(jf, "right_field", "")).strip()
                    if left and right:
                        jk.append(f"{left}={right}")
                    elif left or right:
                        jk.append(left or right)
            elif "<joininfo" in raw_xml_str.lower():
                lefts = re.findall(r'<JoinInfo\s+connection=["\']Left["\']>\s*<Field\s+field=["\']([^"\']+)["\']', raw_xml_str, re.IGNORECASE)
                rights = re.findall(r'<JoinInfo\s+connection=["\']Right["\']>\s*<Field\s+field=["\']([^"\']+)["\']', raw_xml_str, re.IGNORECASE)
                for l, r in zip(lefts, rights):
                    l_clean = l.strip()
                    r_clean = r.strip()
                    if l_clean and r_clean:
                        jk.append(f"{l_clean}={r_clean}")
                    elif l_clean or r_clean:
                        jk.append(l_clean or r_clean)

            # Filter out any malformed tokens: NEVER permit '=' or empty strings
            valid_jk = [k for k in jk if k and k.strip() and k.strip() != "="]
            if valid_jk:
                unique_jk = sorted(list(set(valid_jk)))
                join_keys.extend(unique_jk)
                transformation_signatures.append(f"Join on: {', '.join(unique_jk)}")
            else:
                transformation_signatures.append("Join operation")

        elif ttype == "Summarize":
            sum_fields = getattr(cfg, "summarize_fields", []) or parsed_dict.get("summarize_fields", []) or []
            if not sum_fields and "<summarizefield" in raw_xml_str.lower():
                matches = re.findall(
                    r'<SummarizeField\s+field=["\']([^"\']+)["\']\s+action=["\']([^"\']+)["\'](?:\s+rename=["\']([^"\']*)["\'])?',
                    raw_xml_str,
                    re.IGNORECASE,
                )
                for fld, act, ren in matches:
                    sum_fields.append({"field": fld, "action": act, "rename": ren or ""})

            formatted_sum = format_summarize_fields(sum_fields) if sum_fields else ""
            if formatted_sum:
                aggregations.append(formatted_sum)
                transformation_signatures.append(f"Summarize: {formatted_sum}")
            else:
                transformation_signatures.append("Summarize operation")

        elif ttype in ("Formula", "MultiRowFormula"):
            formula_fields = getattr(cfg, "formula_fields", []) or parsed_dict.get("formula_fields", []) or []
            found_f = False
            for ff in formula_fields:
                f_name = getattr(ff, "field_name", "") or (ff.get("field_name", "") if isinstance(ff, dict) else "")
                f_expr = getattr(ff, "expression", "") or (ff.get("expression", "") if isinstance(ff, dict) else "")
                f_name = str(f_name).strip()
                f_expr = str(f_expr).strip()
                if f_name or f_expr:
                    norm_expr = normalize_expression(f_expr)
                    if f_name and norm_expr:
                        norm_f = f"{f_name}={norm_expr}"
                    elif norm_expr:
                        norm_f = norm_expr
                    else:
                        norm_f = f_name
                    formulas.append(norm_f)
                    transformation_signatures.append(f"Formula: {norm_f}")
                    found_f = True
            if not found_f and "<formulafield" in raw_xml_str.lower():
                matches = re.findall(
                    r'<FormulaField\s+field=["\']([^"\']+)["\']\s+expression=["\']([^"\']+)["\']',
                    raw_xml_str,
                    re.IGNORECASE,
                )
                for f_name, f_expr in matches:
                    f_name = f_name.strip()
                    f_expr = f_expr.strip()
                    norm_expr = normalize_expression(f_expr)
                    if f_name and norm_expr:
                        norm_f = f"{f_name}={norm_expr}"
                    elif norm_expr:
                        norm_f = norm_expr
                    else:
                        norm_f = f_name
                    formulas.append(norm_f)
                    transformation_signatures.append(f"Formula: {norm_f}")
                    found_f = True
            if not found_f:
                transformation_signatures.append(f"{ttype} calculation")

        elif "python" in ttype.lower() or "jupyter" in ttype.lower():
            has_python = True
            transformation_signatures.append("Python script execution")
        elif ttype.lower() == "r":
            has_r = True
            transformation_signatures.append("R statistical script execution")
        elif "macro" in ttype.lower():
            has_macros = True
            transformation_signatures.append(f"Macro: {tool.name}")

    # 5. DAG Topology
    import networkx as nx
    dag_attr = getattr(canonical_res, "dag", None)
    g = getattr(canonical_res, "graph", None) or (getattr(dag_attr, "graph", None) if dag_attr else None) or nx.DiGraph()
    node_count = g.number_of_nodes()
    edge_count = g.number_of_edges()
    dag_depth = nx.dag_longest_path_length(g) if nx.is_directed_acyclic_graph(g) and len(g) > 0 else 0
    branch_points = sum(1 for n in g.nodes() if g.out_degree(n) > 1)
    merge_points = sum(1 for n in g.nodes() if g.in_degree(n) > 1)

    topological_sequence: list[str] = []
    if nx.is_directed_acyclic_graph(g) and len(g) > 0:
        try:
            for node_id in nx.topological_sort(g):
                tool = wf.tools.get(node_id)
                if tool:
                    topological_sequence.append(tool.tool_type)
        except Exception:
            topological_sequence = tool_types

    return WorkflowFingerprint(
        workflow_id=summary.workflow_id,
        workflow_name=summary.filename,
        sources=sorted(clean_sources),
        source_types=source_types,
        source_fields=source_fields,
        production_targets=sorted(clean_targets),
        inspection_sinks=sorted(clean_sinks),
        output_schemas=output_schemas,
        output_grain=sorted(output_grain),
        tool_types=tool_types,
        transformation_signatures=sorted(list(set(transformation_signatures))),
        filters=sorted(list(set(filters))),
        join_keys=sorted(list(set(join_keys))),
        aggregations=sorted(list(set(aggregations))),
        formulas=sorted(list(set(formulas))),
        has_python=has_python,
        has_r=has_r,
        has_macros=has_macros,
        node_count=node_count,
        edge_count=edge_count,
        dag_depth=dag_depth,
        branch_points=branch_points,
        merge_points=merge_points,
        topological_sequence=topological_sequence[:30],
        complexity_level=summary.complexity_level or "LOW",
        complexity_score=summary.complexity_score or 0.0,
        criticality_level=summary.criticality_level or "LOW",
        criticality_score=summary.criticality_score or 0.0,
        downstream_consumers=downstream_consumers or [],
    )


# ---------------------------------------------------------------------------
# 2. Deterministic Cross-Workflow Comparison
# ---------------------------------------------------------------------------
def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets with 0-guard."""
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def compare_workflows(
    fp_a: WorkflowFingerprint,
    fp_b: WorkflowFingerprint,
    target_to_consumers: Optional[dict[str, list[str]]] = None,
) -> WorkflowComparisonEvidence:
    """Deterministically compare two workflow fingerprints across all evidence dimensions."""
    # 1. Source overlap
    src_a = set(fp_a.sources)
    src_b = set(fp_b.sources)
    source_overlap = _jaccard_similarity(src_a, src_b)
    shared_sources = sorted(list(src_a & src_b))

    # 2. Production Target overlap
    tgt_a = set(fp_a.production_targets)
    tgt_b = set(fp_b.production_targets)
    target_overlap = _jaccard_similarity(tgt_a, tgt_b)
    shared_targets = sorted(list(tgt_a & tgt_b))
    distinct_targets_a = sorted(list(tgt_a - tgt_b))
    distinct_targets_b = sorted(list(tgt_b - tgt_a))

    # 3. Output Schema similarity
    all_cols_a = set()
    for cols in fp_a.output_schemas.values():
        all_cols_a.update(cols)
    all_cols_b = set()
    for cols in fp_b.output_schemas.values():
        all_cols_b.update(cols)

    if all_cols_a and all_cols_b:
        schema_similarity = _jaccard_similarity(all_cols_a, all_cols_b)
        schema_diffs = sorted(list((all_cols_a - all_cols_b) | (all_cols_b - all_cols_a)))
    elif not all_cols_a and not all_cols_b:
        schema_similarity = 1.0 if target_overlap > 0.8 else 0.5
        schema_diffs = []
    else:
        schema_similarity = 0.2
        schema_diffs = ["One workflow lacks schema definition"]

    # 4. Output Grain similarity
    grain_a = set(fp_a.output_grain)
    grain_b = set(fp_b.output_grain)
    if grain_a == {"UNKNOWN"} and grain_b == {"UNKNOWN"}:
        grain_similarity = 0.5
        grain_diffs = ["Grain not determinable from workflow definitions"]
    elif "UNKNOWN" in grain_a or "UNKNOWN" in grain_b:
        grain_similarity = 0.5
        grain_diffs = ["Grain partially determinable"]
    else:
        grain_similarity = _jaccard_similarity(grain_a, grain_b)
        grain_diffs = sorted(list((grain_a - grain_b) | (grain_b - grain_a)))

    # 5. Tool type similarity
    tool_type_similarity = _jaccard_similarity(set(fp_a.tool_types), set(fp_b.tool_types))

    # 6. Transformation similarity
    sig_a = set(fp_a.transformation_signatures)
    sig_b = set(fp_b.transformation_signatures)
    transformation_similarity = _jaccard_similarity(sig_a, sig_b)

    # Exclude generic tool-presence markers from shared logic and unique functionality
    shared_logic = sorted([s for s in (sig_a & sig_b) if is_meaningful_evidence(s)])
    unique_a = sorted([s for s in (sig_a - sig_b) if is_meaningful_evidence(s)])
    unique_b = sorted([s for s in (sig_b - sig_a) if is_meaningful_evidence(s)])

    # Check join keys: deduplicate when join condition already represents the join key
    shared_joins = set(fp_a.join_keys) & set(fp_b.join_keys)
    for sj in sorted(list(shared_joins)):
        sj_clean = sj.strip()
        if sj_clean and is_meaningful_evidence(sj_clean):
            # Check if this join key is already part of an existing 'Join on:' entry in shared_logic
            already_represented = any(
                f"Join on: {sj_clean}" in item or f"Join on {sj_clean}" in item or sj_clean in item
                for item in shared_logic
                if "join" in item.lower()
            )
            if not already_represented:
                entry = f"Shared join key: {sj_clean}"
                if entry not in shared_logic and is_meaningful_evidence(entry):
                    shared_logic.append(entry)

    # Check shared filters
    shared_filters = set(fp_a.filters) & set(fp_b.filters)
    for sf in sorted(list(shared_filters)):
        sf_clean = sf.strip()
        if sf_clean and is_meaningful_evidence(sf_clean):
            entry = f"Shared filter predicate: {sf_clean}"
            if entry not in shared_logic and is_meaningful_evidence(entry):
                shared_logic.append(entry)

    # 7. DAG topology similarity
    max_nodes = max(fp_a.node_count, fp_b.node_count, 1)
    node_ratio = min(fp_a.node_count, fp_b.node_count) / max_nodes
    max_depth = max(fp_a.dag_depth, fp_b.dag_depth, 1)
    depth_ratio = min(fp_a.dag_depth, fp_b.dag_depth) / max_depth
    dag_similarity = (node_ratio * 0.5) + (depth_ratio * 0.5)

    # 8. Dependency relationship
    consumers_a = fp_a.downstream_consumers
    consumers_b = fp_b.downstream_consumers
    is_a_feeding_b = bool(set(fp_a.production_targets) & set(fp_b.sources))
    is_b_feeding_a = bool(set(fp_b.production_targets) & set(fp_a.sources))

    dep_status = "NOT_FOUND_IN_PORTFOLIO"
    dep_notes = "No cross-workflow dependency detected within the analysed portfolio."
    if is_a_feeding_b and is_b_feeding_a:
        dep_status = "KNOWN"
        dep_notes = f"Bidirectional pipeline coupling: {fp_a.workflow_name} and {fp_b.workflow_name} exchange datasets."
    elif is_a_feeding_b:
        dep_status = "KNOWN"
        dep_notes = f"Upstream-downstream dependency: {fp_a.workflow_name} produces data ingested by {fp_b.workflow_name}."
    elif is_b_feeding_a:
        dep_status = "KNOWN"
        dep_notes = f"Upstream-downstream dependency: {fp_b.workflow_name} produces data ingested by {fp_a.workflow_name}."
    elif consumers_a or consumers_b:
        dep_status = "KNOWN"
        notes = []
        if consumers_a:
            notes.append(f"{fp_a.workflow_name} consumed by: {', '.join(consumers_a)}")
        if consumers_b:
            notes.append(f"{fp_b.workflow_name} consumed by: {', '.join(consumers_b)}")
        dep_notes = "; ".join(notes)

    dependency_evidence = DependencyEvidence(
        downstream_consumers={
            fp_a.workflow_id: consumers_a,
            fp_b.workflow_id: consumers_b,
        },
        upstream_producers={},
        shared_sources=shared_sources,
        shared_targets=shared_targets,
        dependency_status=dep_status,
        dependency_notes=dep_notes,
    )

    metrics = DeterministicMetrics(
        source_overlap=source_overlap,
        target_overlap=target_overlap,
        transformation_similarity=transformation_similarity,
        schema_similarity=schema_similarity,
        grain_similarity=grain_similarity,
        dag_similarity=dag_similarity,
    )

    # 9. Explainable Opportunity Score (0 - 100)
    target_schema_score = (target_overlap * 0.6) + (schema_similarity * 0.4)
    opp_score = (
        (transformation_similarity * 35.0)
        + (source_overlap * 25.0)
        + (target_schema_score * 20.0)
        + (dag_similarity * 10.0)
        + ((1.0 if shared_sources or shared_targets else 0.0) * 10.0)
    )
    opp_score = max(0.0, min(100.0, opp_score))

    # 10. Evidence Confidence (based on evidence quality/completeness)
    if all_cols_a and all_cols_b and (fp_a.sources or fp_b.sources):
        confidence = "HIGH"
    elif fp_a.sources or fp_b.sources:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return WorkflowComparisonEvidence(
        workflow_a_id=fp_a.workflow_id,
        workflow_a_name=fp_a.workflow_name,
        workflow_b_id=fp_b.workflow_id,
        workflow_b_name=fp_b.workflow_name,
        metrics=metrics,
        shared_logic=shared_logic,
        unique_a=unique_a,
        unique_b=unique_b,
        shared_sources=shared_sources,
        shared_targets=shared_targets,
        distinct_targets_a=distinct_targets_a,
        distinct_targets_b=distinct_targets_b,
        schema_differences=schema_diffs,
        grain_differences=grain_diffs,
        dependency_evidence=dependency_evidence,
        opportunity_score=opp_score,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 3. Deterministic Candidate Detection & Safety Gates
# ---------------------------------------------------------------------------
def detect_candidate_from_comparison(
    comp: WorkflowComparisonEvidence,
    fp_a: WorkflowFingerprint,
    fp_b: WorkflowFingerprint,
) -> Optional[RationalisationCandidate]:
    """Evaluate deterministic safety gates and generate a typed rationalisation candidate.

    Returns None if comparison is NO_ACTION (unrelated workflows), strictly suppressing it.
    """
    m = comp.metrics
    t = RationalisationThresholds

    # Build OutputEvidence
    output_evidence = OutputEvidence(
        production_targets={
            fp_a.workflow_id: fp_a.production_targets,
            fp_b.workflow_id: fp_b.production_targets,
        },
        inspection_sinks={
            fp_a.workflow_id: fp_a.inspection_sinks,
            fp_b.workflow_id: fp_b.inspection_sinks,
        },
        output_schemas={
            fp_a.workflow_id: [f"{col}" for cols in fp_a.output_schemas.values() for col in cols],
            fp_b.workflow_id: [f"{col}" for cols in fp_b.output_schemas.values() for col in cols],
        },
        output_grains={
            fp_a.workflow_id: fp_a.output_grain,
            fp_b.workflow_id: fp_b.output_grain,
        },
        is_equivalent_target=m.target_overlap >= t.RETIRE_TARGET_OVERLAP_MIN,
        is_equivalent_schema=m.schema_similarity >= t.RETIRE_SCHEMA_SIMILARITY_MIN,
        is_equivalent_grain=m.grain_similarity >= 0.70,
    )

    # Build RiskContext
    risk_level = "LOW"
    if fp_a.criticality_level == "HIGH" or fp_b.criticality_level == "HIGH":
        risk_level = "HIGH"
    elif fp_a.criticality_level == "MEDIUM" or fp_b.criticality_level == "MEDIUM":
        risk_level = "MEDIUM"

    risk_context = RiskContext(
        complexity_by_workflow={
            fp_a.workflow_name: fp_a.complexity_level,
            fp_b.workflow_name: fp_b.complexity_level,
        },
        criticality_by_workflow={
            fp_a.workflow_name: fp_a.criticality_level,
            fp_b.workflow_name: fp_b.criticality_level,
        },
        risk_level=risk_level,
        risk_notes=[
            f"{fp_a.workflow_name}: Complexity {fp_a.complexity_level}, Criticality {fp_a.criticality_level}",
            f"{fp_b.workflow_name}: Complexity {fp_b.complexity_level}, Criticality {fp_b.criticality_level}",
        ],
    )

    # Safety Gate 1: Check RETIRE_CANDIDATE
    has_known_consumers = bool(fp_a.downstream_consumers or fp_b.downstream_consumers)
    can_retire = (
        m.target_overlap >= t.RETIRE_TARGET_OVERLAP_MIN
        and m.transformation_similarity >= t.RETIRE_LOGIC_SIMILARITY_MIN
        and output_evidence.is_equivalent_schema
        and output_evidence.is_equivalent_grain
        and len(comp.unique_a) <= t.RETIRE_MAX_UNIQUE_LOGIC_COUNT
        and len(comp.unique_b) <= t.RETIRE_MAX_UNIQUE_LOGIC_COUNT
        and not has_known_consumers
    )

    # Safety Gate 2: Check CONSOLIDATE
    can_consolidate = (
        m.source_overlap >= t.CONSOLIDATE_SOURCE_OVERLAP_MIN
        and m.transformation_similarity >= t.CONSOLIDATE_LOGIC_SIMILARITY_MIN
        and comp.opportunity_score >= t.CONSOLIDATE_MIN_OPPORTUNITY_SCORE
    )

    # Safety Gate 3: Check SHARED_LOGIC
    can_shared_logic = (
        m.transformation_similarity >= t.SHARED_LOGIC_SIMILARITY_MIN
        or (len(comp.shared_logic) >= 2 and comp.opportunity_score >= 30.0)
    )

    # Safety Gate 4: Check REVIEW
    can_review = (
        comp.opportunity_score >= t.MIN_SURFACE_SCORE
        or m.source_overlap >= t.REVIEW_OVERLAP_MIN
        or (len(comp.shared_sources) > 0 and m.transformation_similarity >= 0.20)
    )

    # Determine recommendation and admissible bounds
    if can_retire:
        recommendation_type = "RETIRE_CANDIDATE"
        admissible = ["RETIRE_CANDIDATE", "REVIEW"]
    elif can_consolidate:
        recommendation_type = "CONSOLIDATE"
        admissible = ["CONSOLIDATE", "SHARED_LOGIC", "REVIEW"]
    elif can_shared_logic:
        recommendation_type = "SHARED_LOGIC"
        admissible = ["SHARED_LOGIC", "REVIEW"]
    elif can_review:
        recommendation_type = "REVIEW"
        admissible = ["REVIEW"]
    else:
        # NO_ACTION: Return None so unrelated workflows are never surfaced in the UI!
        return None

    # Deterministic Reasoning & Proposed Strategy
    if recommendation_type == "RETIRE_CANDIDATE":
        reasoning = (
            f"{fp_a.workflow_name} and {fp_b.workflow_name} exhibit strong functional equivalence: "
            f"identical production targets ({', '.join(comp.shared_targets) or 'equivalent targets'}), "
            f"{round(m.transformation_similarity * 100)}% transformation overlap, compatible output schemas, "
            f"and no material unique logic detected. One workflow appears to provide substantially redundant processing."
        )
        proposed_strategy = (
            "Verify operational scheduling, business ownership, and execution history. "
            "Designate one primary workflow and prepare the redundant workflow for phased decommissioning."
        )
        evidence_list = [
            f"{round(m.target_overlap * 100)}% target equivalence across: {', '.join(comp.shared_targets)}",
            f"{round(m.transformation_similarity * 100)}% shared transformation logic",
            "Output schema and data grain alignment confirmed",
            "No active downstream workflow consumers detected in current portfolio",
        ]
        validation_reqs = [
            "Validate operational scheduling and trigger frequencies in Alteryx Server / Gallery",
            "Confirm business owner and SLA commitments before taking retirement action",
            "Inspect historical execution logs to confirm workflow output utilization",
            "Verify external consumers outside the uploaded portfolio do not query this target directly",
        ]
    elif recommendation_type == "CONSOLIDATE":
        reasoning = (
            f"Both workflows consume identical/overlapping source datasets ({', '.join(comp.shared_sources)}) "
            f"and share {round(m.transformation_similarity * 100)}% core operational logic, while generating "
            f"{'distinct production outputs (' + ', '.join(comp.distinct_targets_a + comp.distinct_targets_b) + ')' if (comp.distinct_targets_a or comp.distinct_targets_b) else 'shared targets'}. "
            f"Unified ingestion and transformation would streamline maintenance without compromising deliverables."
        )
        proposed_strategy = (
            "Centralize the common ingestion, filtering, and cleansing pipeline into a unified shared processing layer, "
            "retaining distinct downstream branches for unique analytical outputs."
        )
        evidence_list = [
            f"{round(m.source_overlap * 100)}% source overlap ({len(comp.shared_sources)} shared inputs)",
            f"{round(m.transformation_similarity * 100)}% shared transformation operations",
            f"Distinct production branches: {len(comp.distinct_targets_a)} for {fp_a.workflow_name}, {len(comp.distinct_targets_b)} for {fp_b.workflow_name}",
            f"DAG structural alignment score: {round(m.dag_similarity * 100)}%",
        ]
        validation_reqs = [
            "Confirm output delivery schedules and batch execution windows align",
            "Validate that combined processing runtime meets existing production SLAs",
            "Verify field definitions across both target endpoints remain unchanged",
        ]
    elif recommendation_type == "SHARED_LOGIC":
        reasoning = (
            f"Workflows execute {round(m.transformation_similarity * 100)}% equivalent operational patterns "
            f"({len(comp.shared_logic)} shared logic signatures), but operate on different data assets or serve distinct business purposes. "
            f"Extracting shared transformations into standard reusable assets will reduce maintenance duplication."
        )
        proposed_strategy = (
            "Extract common transformation steps (cleansing, joins, business calculations) into a reusable macro or module, "
            "allowing both workflows to inherit centralized business logic."
        )
        evidence_list = [
            f"{round(m.transformation_similarity * 100)}% transformation logic similarity",
            f"Identified {len(comp.shared_logic)} common operational signatures",
            f"Distinct source assets: {len(fp_a.sources)} in {fp_a.workflow_name}, {len(fp_b.sources)} in {fp_b.workflow_name}",
        ]
        validation_reqs = [
            "Evaluate whether shared operations can be abstracted without introducing runtime dependencies",
            "Confirm macro/module packaging complies with organizational migration standards",
        ]
    else:  # REVIEW
        reasoning = (
            f"Workflows exhibit meaningful structural or operational correlation ({round(comp.opportunity_score, 1)}/100 opportunity score), "
            f"but evidence is incomplete, contains significant unique logic, or differs in criticality ({fp_a.criticality_level} vs {fp_b.criticality_level}). "
            f"Detailed architectural inspection is recommended."
        )
        proposed_strategy = (
            "Conduct peer architectural review to evaluate whether shared assets represent an intentional design pattern "
            "or an uncoordinated duplication of ETL processing."
        )
        evidence_list = [
            f"Opportunity score: {round(comp.opportunity_score, 1)}/100",
            f"{round(m.source_overlap * 100)}% source overlap, {round(m.transformation_similarity * 100)}% logic similarity",
            f"Risk profile: {risk_level} ({fp_a.workflow_name}: {fp_a.criticality_level}, {fp_b.workflow_name}: {fp_b.criticality_level})",
        ]
        validation_reqs = [
            "Clarify functional requirements and business ownership for both assets",
            "Assess migration complexity and regression blast radius before modifying workflows",
        ]

    candidate_id = f"cand_{fp_a.workflow_id[:8]}_{fp_b.workflow_id[:8]}"

    valid_shared = [s for s in comp.shared_logic if is_meaningful_evidence(s)]
    valid_unique_a = [u for u in comp.unique_a if is_meaningful_evidence(u)]
    valid_unique_b = [u for u in comp.unique_b if is_meaningful_evidence(u)]

    unique_func: dict[str, list[str]] = {}
    if valid_unique_a:
        unique_func[fp_a.workflow_name] = valid_unique_a
    if valid_unique_b:
        unique_func[fp_b.workflow_name] = valid_unique_b

    discarded_count = (
        (len(comp.shared_logic) - len(valid_shared))
        + (len(comp.unique_a) - len(valid_unique_a))
        + (len(comp.unique_b) - len(valid_unique_b))
    )

    candidate = RationalisationCandidate(
        candidate_id=candidate_id,
        workflow_ids=[fp_a.workflow_id, fp_b.workflow_id],
        workflow_names=[fp_a.workflow_name, fp_b.workflow_name],
        recommendation_type=recommendation_type,
        confidence=comp.confidence,
        opportunity_score=comp.opportunity_score,
        reasoning=reasoning,
        evidence=evidence_list,
        shared_logic=valid_shared,
        unique_functionality=unique_func,
        proposed_strategy=proposed_strategy,
        validation_requirements=validation_reqs,
        deterministic_metrics=m,
        output_evidence=output_evidence,
        dependency_evidence=comp.dependency_evidence,
        risk_context=risk_context,
        admissible_recommendations=admissible,
        llm_enrichment_status="DETERMINISTIC_BASELINE",
    )

    logger.info(
        "[RATIONALISATION EVIDENCE] candidate=%s shared_count=%d unique_counts=%s discarded_invalid=%d",
        candidate.candidate_id,
        len(valid_shared),
        {k: len(v) for k, v in unique_func.items()},
        discarded_count,
    )

    return candidate


# ---------------------------------------------------------------------------
# 4. LLM Semantic Interpretation & Deterministic Validation
# ---------------------------------------------------------------------------
def validate_llm_rationalisation_response(
    candidate: RationalisationCandidate,
    parsed_json: dict[str, Any],
    valid_wf_ids: set[str],
    valid_dataset_names: set[str],
) -> tuple[bool, str]:
    """Strictly validate LLM response against canonical evidence boundaries.

    Returns (is_valid, failure_reason).
    """
    rec = parsed_json.get("recommendation") or parsed_json.get("recommendation_type")
    if rec not in candidate.admissible_recommendations:
        return False, f"Recommendation '{rec}' violates deterministic admissibility boundary: {candidate.admissible_recommendations}"

    resp_wf_ids = parsed_json.get("workflow_ids", [])
    if resp_wf_ids and set(resp_wf_ids) != set(candidate.workflow_ids):
        return False, f"Workflow IDs in response {resp_wf_ids} do not match candidate {candidate.workflow_ids}"

    for wid in resp_wf_ids:
        if wid not in valid_wf_ids:
            return False, f"Hallucinated workflow ID detected: {wid}"

    reasoning = parsed_json.get("reasoning", "")
    if not reasoning or len(reasoning.strip()) < 10:
        return False, "Reasoning is empty or insufficient"

    return True, "Valid"


def enrich_candidate_with_llm(
    candidate: RationalisationCandidate,
    generator: Optional[LLMNarrativeGenerator],
    valid_wf_ids: set[str],
    valid_dataset_names: set[str],
) -> RationalisationCandidate:
    """Enrich candidate with LLM semantic interpretation using existing LLM infrastructure.

    Strictly preserves deterministic metrics, opportunity score, and falls back to
    deterministic recommendation on any validation failure.
    """
    if (
        generator is None
        or not getattr(generator, "client", None)
        or not getattr(generator.client, "is_available", True)
    ):
        candidate.llm_enrichment_status = "DETERMINISTIC_BASELINE"
        return candidate

    evidence_payload = {
        "candidate_id": candidate.candidate_id,
        "workflows": candidate.workflow_names,
        "workflow_ids": candidate.workflow_ids,
        "deterministic_recommendation": candidate.recommendation_type,
        "admissible_recommendations": candidate.admissible_recommendations,
        "opportunity_score": candidate.opportunity_score,
        "deterministic_metrics": candidate.deterministic_metrics.to_dict(),
        "shared_logic": candidate.shared_logic,
        "unique_functionality": candidate.unique_functionality,
        "shared_sources": candidate.dependency_evidence.shared_sources,
        "shared_targets": candidate.dependency_evidence.shared_targets,
        "dependencies": candidate.dependency_evidence.dependency_notes,
    }

    cache_key: str | None = None
    if getattr(generator, "_cache", None) and hasattr(generator.client, "model_name"):
        try:
            cache_key = compute_cache_key(
                workflow_id=candidate.candidate_id or "_".join(candidate.workflow_ids),
                scope_key="candidate_rationalisation",
                prompt_version="v1",
                model_name=generator.client.model_name,
                facts_payload=evidence_payload,
            )
            cached = generator._cache.get(cache_key)
            if cached is not None:
                logger.info("[Rationalisation LLM CACHE] status=HIT for candidate %s", candidate.candidate_id)
                raw_response = cached.text
        except Exception:
            cache_key = None

    system_prompt = (
        "You are a Principal Enterprise Data Architect and ETL Migration Specialist.\n"
        "Your role is to interpret deterministic ETL portfolio evidence and explain rationalisation opportunities.\n"
        "STRICT INVARIANTS:\n"
        "1. Ground every statement strictly in the provided evidence. NEVER invent workflows, tables, or operational facts.\n"
        f"2. Your recommendation MUST be one of these admissible options: {', '.join(candidate.admissible_recommendations)}.\n"
        "3. Provide business-friendly, professional explanations of why the logic overlaps and what strategy to follow.\n"
        "4. Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "recommendation": "CONSOLIDATE | RETIRE_CANDIDATE | SHARED_LOGIC | REVIEW",\n'
        '  "workflow_ids": ["<id>", ...],\n'
        '  "reasoning": "<concise executive explanation of overlap and business impact>",\n'
        '  "proposed_strategy": "<actionable target architectural approach>",\n'
        '  "validation_requirements": ["<key validation step>", ...]\n'
        "}"
    )

    user_prompt = (
        f"Evaluate the following deterministic ETL rationalisation candidate:\n\n"
        f"{json.dumps(evidence_payload, indent=2)}\n\n"
        f"Structured JSON Response:"
    )

    raw_response: str | None = None
    if cache_key and getattr(generator, "_cache", None):
        cached = generator._cache.get(cache_key)
        if cached is not None:
            raw_response = cached.text

    if raw_response is None:
        try:
            raw_response = generator.client.generate(system_prompt, user_prompt, max_tokens=1500)
        except Exception as e:
            logger.warning("[Rationalisation LLM] Error calling LLM: %s — falling back to deterministic baseline.", e)
            candidate.llm_enrichment_status = "DETERMINISTIC_FALLBACK"
            return candidate

    if not raw_response or not raw_response.strip():
        candidate.llm_enrichment_status = "DETERMINISTIC_FALLBACK"
        return candidate

    try:
        clean_text = raw_response.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[-1]
            if clean_text.endswith("```"):
                clean_text = clean_text.rsplit("```", 1)[0]
            clean_text = clean_text.strip()
        parsed = json.loads(clean_text)

        is_valid, fail_reason = validate_llm_rationalisation_response(
            candidate, parsed, valid_wf_ids, valid_dataset_names
        )

        if is_valid:
            rec = parsed.get("recommendation") or parsed.get("recommendation_type")
            if rec in candidate.admissible_recommendations:
                candidate.recommendation_type = rec
            candidate.reasoning = parsed.get("reasoning", candidate.reasoning).strip()
            if parsed.get("proposed_strategy"):
                candidate.proposed_strategy = parsed.get("proposed_strategy").strip()
            if parsed.get("validation_requirements") and isinstance(parsed.get("validation_requirements"), list):
                candidate.validation_requirements = [
                    str(vr).strip() for vr in parsed.get("validation_requirements") if str(vr).strip()
                ]
            candidate.llm_enrichment_status = "ENRICHED"

            # Cache successful valid result
            if cache_key and getattr(generator, "_cache", None):
                generator._cache.set(cache_key, NarrativeResult(
                    text=clean_text,
                    is_cached=False,
                    model=getattr(generator.client, "model_name", "unknown"),
                    source="LLM",
                ))
        else:
            logger.warning("[Rationalisation LLM Validation Failed] %s — falling back to deterministic baseline.", fail_reason)
            candidate.llm_enrichment_status = "VALIDATION_FAILED"

    except Exception as e:
        logger.warning("[Rationalisation LLM] Error processing response: %s — falling back to deterministic baseline.", e)
        candidate.llm_enrichment_status = "DETERMINISTIC_FALLBACK"

    return candidate


# ---------------------------------------------------------------------------
# 5. Full Portfolio Rationalisation Orchestrator
# ---------------------------------------------------------------------------
def build_rationalisation_analysis(
    portfolio: PortfolioAnalysis,
    successful_results: dict[str, CanonicalAnalysisResult],
    generator: Optional[LLMNarrativeGenerator] = None,
    use_llm: bool = True,
) -> RationalisationAnalysis:
    """Build complete, production-grade ETL Rationalisation analysis across a portfolio."""
    # Resolve default generator if caller requested LLM but didn't provide one
    if use_llm and generator is None:
        try:
            gen = get_default_generator()
            if getattr(gen, "client", None) and getattr(gen.client, "is_available", False):
                generator = gen
        except Exception:
            generator = None
    success_summaries = [w for w in portfolio.workflows if w.status == "SUCCESS" and w.workflow_id in successful_results]

    if len(success_summaries) < 1:
        return RationalisationAnalysis(
            portfolio_id=portfolio.portfolio_id,
            candidates=[],
            total_opportunities=0,
            recommendation_counts={"CONSOLIDATE": 0, "RETIRE_CANDIDATE": 0, "SHARED_LOGIC": 0, "REVIEW": 0},
            analysed_workflow_count=len(portfolio.workflows),
        )

    # 1. Build portfolio consumer index (which workflows consume target X)
    target_to_consumers: dict[str, list[str]] = {}
    for summary in success_summaries:
        for tgt in summary.targets:
            norm_tgt = normalize_name(tgt)
            if not norm_tgt:
                continue
            for other in success_summaries:
                if other.workflow_id == summary.workflow_id:
                    continue
                other_sources = [normalize_name(s) for s in other.sources]
                if norm_tgt in other_sources:
                    target_to_consumers.setdefault(norm_tgt, []).append(other.filename)

    # 2. Build fingerprints ONCE per workflow (O(N) operation to preserve performance)
    fingerprints: dict[str, WorkflowFingerprint] = {}
    valid_wf_ids: set[str] = set()
    valid_dataset_names: set[str] = set()

    for summary in success_summaries:
        res = successful_results[summary.workflow_id]
        consumers: list[str] = []
        for tgt in summary.targets:
            norm_t = normalize_name(tgt)
            if norm_t in target_to_consumers:
                consumers.extend(target_to_consumers[norm_t])
        consumers = sorted(list(set(consumers)))

        fp = build_workflow_fingerprint(summary, res, downstream_consumers=consumers)
        fingerprints[summary.workflow_id] = fp
        valid_wf_ids.add(summary.workflow_id)
        valid_dataset_names.update(fp.sources)
        valid_dataset_names.update(fp.production_targets)

    # 3. Pairwise comparisons & candidate detection (O(N^2) over pre-computed fingerprints)
    candidates: list[RationalisationCandidate] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i in range(len(success_summaries)):
        for j in range(i + 1, len(success_summaries)):
            id_a = success_summaries[i].workflow_id
            id_b = success_summaries[j].workflow_id
            pair_key = tuple(sorted([id_a, id_b]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            fp_a = fingerprints[id_a]
            fp_b = fingerprints[id_b]

            comp = compare_workflows(fp_a, fp_b, target_to_consumers)
            cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

            if cand is not None:
                if use_llm and generator:
                    cand = enrich_candidate_with_llm(cand, generator, valid_wf_ids, valid_dataset_names)
                candidates.append(cand)

    # 4. Check single-workflow inspection-sink-only workflows (zero production targets)
    for summary in success_summaries:
        fp = fingerprints[summary.workflow_id]
        if len(fp.production_targets) == 0 and len(fp.inspection_sinks) > 0:
            cand_id = f"cand_sink_{fp.workflow_id[:8]}"
            if not any(cand_id == c.candidate_id for c in candidates):
                candidates.append(
                    RationalisationCandidate(
                        candidate_id=cand_id,
                        workflow_ids=[fp.workflow_id],
                        workflow_names=[fp.workflow_name],
                        recommendation_type="REVIEW",
                        confidence="HIGH",
                        opportunity_score=35.0,
                        reasoning=(
                            f"{fp.workflow_name} produces no production deliverables and terminates exclusively in "
                            f"inspection sinks ({', '.join(fp.inspection_sinks)}). It likely represents an ad-hoc data "
                            f"investigation or unfinished development asset."
                        ),
                        evidence=[
                            f"Terminal inspection sinks: {', '.join(fp.inspection_sinks)}",
                            "Zero configured production deliverables",
                            f"{fp.node_count} tools, {fp.edge_count} connections",
                        ],
                        shared_logic=[],
                        unique_functionality={fp.workflow_name: ["Inspection/Browse sink only"]},
                        proposed_strategy="Confirm whether this workflow is intended for production deployment or can be retired as a temporary exploratory asset.",
                        validation_requirements=[
                            "Confirm with data team if this workflow is actively used for manual diagnostics",
                            "Verify no external schedule triggers this workflow in production",
                        ],
                        admissible_recommendations=["REVIEW", "RETIRE_CANDIDATE"],
                        llm_enrichment_status="DETERMINISTIC_BASELINE",
                    )
                )

    # Sort candidates by opportunity score descending
    candidates.sort(key=lambda c: c.opportunity_score, reverse=True)

    # 5. Aggregate recommendation counts
    rec_counts = {
        "CONSOLIDATE": sum(1 for c in candidates if c.recommendation_type == "CONSOLIDATE"),
        "RETIRE_CANDIDATE": sum(1 for c in candidates if c.recommendation_type == "RETIRE_CANDIDATE"),
        "SHARED_LOGIC": sum(1 for c in candidates if c.recommendation_type == "SHARED_LOGIC"),
        "REVIEW": sum(1 for c in candidates if c.recommendation_type == "REVIEW"),
    }

    return RationalisationAnalysis(
        portfolio_id=portfolio.portfolio_id,
        candidates=candidates,
        total_opportunities=len(candidates),
        recommendation_counts=rec_counts,
        analysed_workflow_count=len(portfolio.workflows),
    )
