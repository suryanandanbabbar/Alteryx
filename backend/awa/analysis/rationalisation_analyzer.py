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
    ColumnEvidence,
    ConsolidationDecision,
    DataSubsumptionEvidence,
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

    # Consolidation boundaries (hard gate: source metadata overlap must be strictly > 60%)
    CONSOLIDATE_SOURCE_OVERLAP_MIN: float = 0.60
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
    clean = str(name).replace("\\", "/").strip()
    clean = Path(clean).name.strip().lower()
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


def normalize_field_name(name: str) -> str:
    """Normalize column/field name conservatively for deterministic matching."""
    if not name:
        return ""
    clean = str(name).strip().lower()
    clean = re.sub(r"[^a-z0-9]", "_", clean)
    return re.sub(r"_+", "_", clean).strip("_")


def extract_workflow_column_and_data_evidence(
    summary: PortfolioWorkflowSummary,
    canonical_res: CanonicalAnalysisResult,
) -> tuple[dict[str, ColumnEvidence], list[str], list[str], int, list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically extract canonical column evidence, required fields, available fields,
    sample data from <Data><r><c>, and structured operations from canonical workflow analysis.
    """
    import xml.etree.ElementTree as ET
    import re
    wf = canonical_res.workflow
    canonical_columns: dict[str, ColumnEvidence] = {}
    required_columns: set[str] = set()
    available_columns: set[str] = set()
    rows_inspected = 0
    sample_data_evidence: list[dict[str, Any]] = []
    operations_summary: list[dict[str, Any]] = []

    # 1. Inspect all tools in canonical AST
    for tid, tool in sorted(wf.tools.items(), key=lambda x: str(x[0])):
        ttype = tool.tool_type
        cfg = tool.configuration
        raw_xml = cfg.raw_xml if (cfg and hasattr(cfg, "raw_xml") and isinstance(cfg.raw_xml, str)) else ""
        parsed_dict = cfg.parsed if (cfg and hasattr(cfg, "parsed") and isinstance(cfg.parsed, dict)) else {}

        root = None
        if raw_xml:
            try:
                root = ET.fromstring(f"<root>{raw_xml}</root>")
            except Exception:
                root = None

        # Output fields from MetaInfo/RecordInfo on the tool
        if hasattr(tool, "output_fields") and tool.output_fields:
            for f in tool.output_fields:
                fname = getattr(f, "name", str(f))
                if fname and fname != "*Unknown":
                    norm = normalize_field_name(fname)
                    available_columns.add(norm)
                    if norm not in canonical_columns:
                        canonical_columns[norm] = ColumnEvidence(
                            original_name=fname,
                            normalized_name=norm,
                            source_dataset=tool.name or f"{ttype} (Tool #{tid})",
                            source_tool_id=str(tid),
                            source_tool_type=ttype,
                            provenance=f"RecordInfo: {ttype} (Tool #{tid})",
                            is_required=False,
                        )

        # A. TextInput (<Fields><Field name="..." /></Fields> and <Data><r><c>...</c></r></Data>)
        if ttype == "TextInput":
            declared_fields = []
            if root is not None:
                declared_fields = [f.get("name") for f in root.findall(".//Fields/Field") if f.get("name")]
            if not declared_fields:
                declared_fields = parsed_dict.get("fields", [])

            rows = []
            if root is not None:
                for r in root.findall(".//Data/r"):
                    rows.append([c.text or "" for c in r.findall("c")])
            if not rows:
                rows = parsed_dict.get("rows", [])

            rows_inspected += len(rows)
            effective_field_names: list[str] = []
            data_rows: list[list[str]] = []

            # Check if row 0 contains delimited CSV headers (e.g. <c>Claim_ID,Diagnosis_Type,ICD_Code</c>)
            if rows and len(rows[0]) == 1 and rows[0][0]:
                r0_text = rows[0][0].strip()
                delims = [",", "\t", "|", ";"]
                best_delim = None
                best_count = 0
                for d in delims:
                    cnt = r0_text.count(d)
                    if cnt > best_count:
                        best_count = cnt
                        best_delim = d
                if best_delim and best_count >= 1:
                    tokens = [t.strip() for t in r0_text.split(best_delim) if t.strip()]
                    if len(tokens) > 1 and all(re.match(r'^[A-Za-z0-9_\s\.\-]+$', t) and not re.match(r'^\d+(\.\d+)?$', t) for t in tokens):
                        effective_field_names = tokens
                        for r in rows[1:]:
                            if r and r[0]:
                                data_rows.append([c.strip() for c in r[0].split(best_delim)])

            # Check if multi-column rows where declared fields are generic (Field_1) and row 0 has header names
            if not effective_field_names and rows and len(rows[0]) > 1:
                is_generic = (
                    not declared_fields
                    or all(re.match(r'^(field_?\d+|f\d+|\d+)$', f.lower()) for f in declared_fields if f)
                )
                r0_cells = [c.strip() for c in rows[0]]
                if is_generic and all(re.match(r'^[A-Za-z0-9_\s\.\-]+$', c) and not re.match(r'^\d+(\.\d+)?$', c) for c in r0_cells if c):
                    effective_field_names = r0_cells
                    data_rows = rows[1:]

            # Standard declared fields
            if not effective_field_names:
                effective_field_names = [f for f in declared_fields if f and f != "*Unknown"]
                data_rows = rows

            for idx, f_name in enumerate(effective_field_names):
                norm = normalize_field_name(f_name)
                samples = []
                for r in data_rows:
                    if idx < len(r) and r[idx]:
                        val = str(r[idx]).strip()
                        if val and val not in samples:
                            samples.append(val)
                if samples:
                    sample_data_evidence.append({
                        "field": f_name,
                        "normalized": norm,
                        "tool_id": str(tid),
                        "tool_type": ttype,
                        "samples": samples[:5],
                        "row_count": len(rows),
                    })
                col_ev = ColumnEvidence(
                    original_name=f_name,
                    normalized_name=norm,
                    source_dataset=f"TextInput (Tool #{tid})",
                    source_tool_id=str(tid),
                    source_tool_type=ttype,
                    provenance=f"TextInput #{tid} embedded data",
                    sample_values=samples[:5],
                    is_required=True,
                )
                canonical_columns[norm] = col_ev
                available_columns.add(norm)

        # B. File/DB Input RecordInfo (<RecordInfo><Field name="..." source="..." /></RecordInfo>)
        if root is not None:
            for f_el in root.findall(".//RecordInfo/Field"):
                f_name = f_el.get("name")
                f_source = f_el.get("source", "")
                if f_name and f_name != "*Unknown":
                    norm = normalize_field_name(f_name)
                    col_ev = ColumnEvidence(
                        original_name=f_name,
                        normalized_name=norm,
                        source_dataset=tool.name or f"Input (Tool #{tid})",
                        source_tool_id=str(tid),
                        source_tool_type=ttype,
                        provenance=f"RecordInfo: {f_source or tool.name or 'Configured Stream'} (Tool #{tid})",
                        is_required=True,
                    )
                    canonical_columns[norm] = col_ev
                    available_columns.add(norm)

        # C. Select / AlteryxSelect & Join SelectConfiguration (<SelectFields><SelectField field="..." rename="..." selected="..." /></SelectFields>)
        if root is not None:
            for sf_el in root.findall(".//SelectFields/SelectField"):
                sf_fld = sf_el.get("field")
                sf_ren = sf_el.get("rename")
                sf_sel = sf_el.get("selected", "True")
                if sf_fld and sf_fld != "*Unknown":
                    norm_fld = normalize_field_name(sf_fld)
                    if sf_sel.lower() != "false":
                        available_columns.add(norm_fld)
                        if sf_fld.startswith("Left_") or sf_fld.startswith("Right_"):
                            available_columns.add(normalize_field_name(sf_fld[5:]))
                        if sf_ren and sf_ren != "*Unknown":
                            norm_ren = normalize_field_name(sf_ren)
                            available_columns.add(norm_ren)
                            if sf_ren.startswith("Left_") or sf_ren.startswith("Right_"):
                                available_columns.add(normalize_field_name(sf_ren[5:]))
                            col_ev = ColumnEvidence(
                                original_name=sf_ren,
                                normalized_name=norm_ren,
                                source_dataset=f"Select (Tool #{tid})",
                                source_tool_id=str(tid),
                                source_tool_type=ttype,
                                provenance=f"Select rename from {sf_fld} (Tool #{tid})",
                                is_required=False,
                            )
                            canonical_columns[norm_ren] = col_ev

        # D. Formula fields (<FormulaField field="..." expression="..." />)
        formula_fields = parsed_dict.get("formula_fields", [])
        if not formula_fields and root is not None:
            for ff in root.findall(".//FormulaField"):
                formula_fields.append({"field": ff.get("field"), "expression": ff.get("expression")})
        for ff in formula_fields:
            fn = ff.get("field") if isinstance(ff, dict) else getattr(ff, "field_name", "")
            expr = ff.get("expression") if isinstance(ff, dict) else getattr(ff, "expression", "")
            if fn and fn != "*Unknown":
                norm = normalize_field_name(fn)
                col_ev = ColumnEvidence(
                    original_name=fn,
                    normalized_name=norm,
                    source_dataset="Formula Transformation",
                    source_tool_id=str(tid),
                    source_tool_type=ttype,
                    provenance=f"Formula [{fn} = {expr}] (Tool #{tid})",
                    is_required=False,
                )
                canonical_columns[norm] = col_ev
                available_columns.add(norm)
                # Extract referenced input fields in the formula expression (e.g. [Claim_Date], [Loss_Amount])
                if expr:
                    ref_flds = re.findall(r'\[([^\]]+)\]', expr)
                    for rf in ref_flds:
                        norm_rf = normalize_field_name(rf)
                        if norm_rf and norm_rf != "*unknown":
                            required_columns.add(norm_rf)
                            if norm_rf not in canonical_columns:
                                canonical_columns[norm_rf] = ColumnEvidence(
                                    original_name=rf,
                                    normalized_name=norm_rf,
                                    source_dataset=f"Formula Input (Tool #{tid})",
                                    source_tool_id=str(tid),
                                    source_tool_type=ttype,
                                    provenance=f"Formula input in [{expr}] (Tool #{tid})",
                                    is_required=True,
                                )
                operations_summary.append({
                    "tool_id": str(tid),
                    "tool_type": "Formula",
                    "operation": f"Formula: {fn} = {expr}",
                    "target_field": fn,
                    "expression": expr,
                })

        # E. Unique (<UniqueFields><Field field="..." /></UniqueFields>)
        unique_fields = parsed_dict.get("unique_fields", [])
        if not unique_fields and root is not None:
            unique_fields = [f.get("field") for f in root.findall(".//UniqueFields/Field") if f.get("field")]
        if unique_fields:
            for uf in unique_fields:
                norm = normalize_field_name(uf)
                required_columns.add(norm)
                if norm not in canonical_columns:
                    canonical_columns[norm] = ColumnEvidence(
                        original_name=uf,
                        normalized_name=norm,
                        source_dataset=f"Unique (Tool #{tid})",
                        source_tool_id=str(tid),
                        source_tool_type=ttype,
                        provenance=f"Unique deduplication key (Tool #{tid})",
                        is_required=True,
                    )
            fields_str = ", ".join(unique_fields)
            operations_summary.append({
                "tool_id": str(tid),
                "tool_type": "Unique",
                "operation": f"Unique deduplication on {fields_str}",
                "fields": unique_fields,
            })

        # F. Union
        if ttype == "Union":
            mode = parsed_dict.get("by_name_or_pos") or "ByName"
            operations_summary.append({
                "tool_id": str(tid),
                "tool_type": "Union",
                "operation": f"Union of input datasets (Mode: {mode})",
                "mode": mode,
            })

        # G. Join
        join_fields = parsed_dict.get("join_fields", [])
        if not join_fields and root is not None:
            left_flds = [f.get("field") for f in root.findall(".//JoinInfo[@connection='Left']/Field") if f.get("field")]
            right_flds = [f.get("field") for f in root.findall(".//JoinInfo[@connection='Right']/Field") if f.get("field")]
            for lf, rf in zip(left_flds, right_flds):
                join_fields.append({"left": lf, "right": rf})
        if join_fields:
            jk_desc = []
            for jf in join_fields:
                l = jf.get("left") if isinstance(jf, dict) else getattr(jf, "left", "")
                r = jf.get("right") if isinstance(jf, dict) else getattr(jf, "right", "")
                if l:
                    norm_l = normalize_field_name(l)
                    required_columns.add(norm_l)
                    if norm_l not in canonical_columns:
                        canonical_columns[norm_l] = ColumnEvidence(
                            original_name=l,
                            normalized_name=norm_l,
                            source_dataset=f"Join (Tool #{tid})",
                            source_tool_id=str(tid),
                            source_tool_type=ttype,
                            provenance=f"Join key Left: {l} (Tool #{tid})",
                            is_required=True,
                        )
                if r:
                    norm_r = normalize_field_name(r)
                    required_columns.add(norm_r)
                    if norm_r not in canonical_columns:
                        canonical_columns[norm_r] = ColumnEvidence(
                            original_name=r,
                            normalized_name=norm_r,
                            source_dataset=f"Join (Tool #{tid})",
                            source_tool_id=str(tid),
                            source_tool_type=ttype,
                            provenance=f"Join key Right: {r} (Tool #{tid})",
                            is_required=True,
                        )
                if l and r: jk_desc.append(f"{l}={r}")
            jk_str = ", ".join(jk_desc)
            operations_summary.append({
                "tool_id": str(tid),
                "tool_type": "Join",
                "operation": f"Join on {jk_str}",
                "keys": jk_desc,
            })

        # H. Summarize
        sum_fields = parsed_dict.get("summarize_fields", [])
        if sum_fields:
            for sf in sum_fields:
                fld = sf.get("field") if isinstance(sf, dict) else getattr(sf, "field", "")
                if fld:
                    norm = normalize_field_name(fld)
                    required_columns.add(norm)
                ren = sf.get("rename") if isinstance(sf, dict) else getattr(sf, "rename", "")
                if ren:
                    available_columns.add(normalize_field_name(ren))
            operations_summary.append({
                "tool_id": str(tid),
                "tool_type": "Summarize",
                "operation": f"Summarize aggregation ({len(sum_fields)} fields)",
                "fields": sum_fields,
            })

        # I. Filter
        if ttype == "Filter":
            expr = parsed_dict.get("expression") or ""
            if root is not None and not expr:
                expr = root.findtext(".//Expression") or ""
            simple_fld = root.findtext(".//Simple/Field") if root is not None else None
            if simple_fld:
                norm_sf = normalize_field_name(simple_fld)
                required_columns.add(norm_sf)
                if norm_sf not in canonical_columns:
                    canonical_columns[norm_sf] = ColumnEvidence(
                        original_name=simple_fld,
                        normalized_name=norm_sf,
                        source_dataset=f"Filter (Tool #{tid})",
                        source_tool_id=str(tid),
                        source_tool_type=ttype,
                        provenance=f"Filter field: {simple_fld} (Tool #{tid})",
                        is_required=True,
                    )
            if expr:
                ref_flds = re.findall(r'\[([^\]]+)\]', expr)
                for rf in ref_flds:
                    norm_rf = normalize_field_name(rf)
                    if norm_rf and norm_rf != "*unknown":
                        required_columns.add(norm_rf)
                        if norm_rf not in canonical_columns:
                            canonical_columns[norm_rf] = ColumnEvidence(
                                original_name=rf,
                                normalized_name=norm_rf,
                                source_dataset=f"Filter (Tool #{tid})",
                                source_tool_id=str(tid),
                                source_tool_type=ttype,
                                provenance=f"Filter predicate [{expr}] (Tool #{tid})",
                                is_required=True,
                            )
                operations_summary.append({
                    "tool_id": str(tid),
                    "tool_type": "Filter",
                    "operation": f"Filter predicate: {expr}",
                    "expression": expr,
                })

        # J. Sort
        sort_fields = parsed_dict.get("sort_fields", [])
        if sort_fields:
            sf_names = [sf.get("field") for sf in sort_fields if isinstance(sf, dict) and sf.get("field")]
            for sfn in sf_names:
                required_columns.add(normalize_field_name(sfn))
            operations_summary.append({
                "tool_id": str(tid),
                "tool_type": "Sort",
                "operation": f"Sort on {', '.join(sf_names)}",
                "fields": sf_names,
            })

    # 2. Check STTM and lineage for any additional canonical field definitions
    lineage_attr = getattr(canonical_res, "lineage", None)
    if lineage_attr and hasattr(lineage_attr, "source_fields"):
        for src, flds in lineage_attr.source_fields.items():
            for f in flds:
                fname = getattr(f, "name", str(f))
                if fname and fname != "*Unknown":
                    norm = normalize_field_name(fname)
                    if norm not in canonical_columns:
                        col_ev = ColumnEvidence(
                            original_name=fname,
                            normalized_name=norm,
                            source_dataset=src,
                            provenance=f"Lineage source: {src}",
                            is_required=True,
                        )
                        canonical_columns[norm] = col_ev
                    available_columns.add(norm)

    return (
        canonical_columns,
        sorted(list(required_columns)),
        sorted(list(available_columns)),
        rows_inspected,
        sample_data_evidence,
        operations_summary,
    )


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

    target_keys = clean_targets if clean_targets else (clean_sinks if clean_sinks else ["outputs"])

    # Output schemas & fields from STTM, lineage_paths, or output_schema
    output_schemas: dict[str, list[str]] = {}
    schema_attr = getattr(canonical_res, "output_schema", None)
    if schema_attr and hasattr(schema_attr, "fields"):
        fnames = [getattr(f, "name", str(f)) for f in schema_attr.fields if getattr(f, "name", str(f)) and getattr(f, "name", str(f)) != "*Unknown"]
        for t in target_keys:
            output_schemas[t] = sorted(list(set(fnames)))

    sttm_doc = getattr(canonical_res, "sttm", None)
    if sttm_doc and hasattr(sttm_doc, "mappings") and isinstance(sttm_doc.mappings, list):
        for m in sttm_doc.mappings:
            src_fld = getattr(m, "source_field", "")
            tgt_fld = getattr(m, "target_field", "")
            if src_fld and src_fld != "*Unknown":
                source_fields.setdefault("sources", []).append(src_fld)
            if tgt_fld and tgt_fld != "*Unknown":
                for t in target_keys:
                    output_schemas.setdefault(t, []).append(tgt_fld)

    lineage_paths = getattr(canonical_res, "lineage_paths", None)
    if lineage_paths and isinstance(lineage_paths, list):
        for lp in lineage_paths:
            src_fld = getattr(lp, "source_field", "")
            tgt_fld = getattr(lp, "target_field", "")
            if src_fld and src_fld != "*Unknown":
                source_fields.setdefault("sources", []).append(src_fld)
            if tgt_fld and tgt_fld != "*Unknown":
                for t in target_keys:
                    output_schemas.setdefault(t, []).append(tgt_fld)

    if wf and hasattr(wf, "tools") and isinstance(wf.tools, dict):
        for tool in wf.tools.values():
            if getattr(tool, "tool_type", "") in ("DbFileOutput", "Output", "PublishToTableauServer") or "output" in getattr(tool, "plugin", "").lower():
                if getattr(tool, "output_fields", None):
                    for f in tool.output_fields:
                        fname = getattr(f, "name", str(f))
                        if fname and fname != "*Unknown":
                            for t in target_keys:
                                output_schemas.setdefault(t, []).append(fname)

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

    canonical_columns, req_cols, avail_cols, rows_inspected, sample_ev, ops_summary = (
        extract_workflow_column_and_data_evidence(summary, canonical_res)
    )

    # Enrich source_fields map from canonical column provenance and datasets
    for col_ev in canonical_columns.values():
        ds = col_ev.source_dataset or "sources"
        norm_ds = normalize_name(ds) or ds
        source_fields.setdefault(norm_ds, []).append(col_ev.original_name)
    for k in list(source_fields.keys()):
        source_fields[k] = sorted(list(set(source_fields[k])))

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
        frequency=summary.frequency or (
            summary.factor_assessments.get("frequency", {}).get("display_value")
            if hasattr(summary, "factor_assessments") and isinstance(summary.factor_assessments, dict)
            else "Not documented"
        ) or "Not documented",
        downstream_consumers=downstream_consumers or [],
        canonical_columns=canonical_columns,
        required_columns=req_cols,
        available_columns=avail_cols,
        raw_data_rows_inspected=rows_inspected,
        sample_data_evidence=sample_ev,
        operations_summary=ops_summary,
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
    # 1. Exact Source Identity match
    src_a = {normalize_name(s) for s in fp_a.sources if s and s != "*Unknown" and "unknown" not in s.lower() and normalize_name(s)}
    src_b = {normalize_name(s) for s in fp_b.sources if s and s != "*Unknown" and "unknown" not in s.lower() and normalize_name(s)}
    shared_sources = sorted(list(src_a & src_b))

    # Field-level Source Metadata match (from canonical columns, available columns, required columns, and source fields)
    flds_a = set()
    for k in fp_a.canonical_columns.keys():
        if k:
            flds_a.add(normalize_field_name(k))
    for f in fp_a.available_columns:
        if f:
            flds_a.add(normalize_field_name(f))
    for f in fp_a.required_columns:
        if f:
            flds_a.add(normalize_field_name(f))
    for flist in fp_a.source_fields.values():
        for f in flist:
            if f:
                flds_a.add(normalize_field_name(f))
    flds_a.discard("")

    flds_b = set()
    for k in fp_b.canonical_columns.keys():
        if k:
            flds_b.add(normalize_field_name(k))
    for f in fp_b.available_columns:
        if f:
            flds_b.add(normalize_field_name(f))
    for f in fp_b.required_columns:
        if f:
            flds_b.add(normalize_field_name(f))
    for flist in fp_b.source_fields.values():
        for f in flist:
            if f:
                flds_b.add(normalize_field_name(f))
    flds_b.discard("")

    shared_source_fields = sorted(list(flds_a & flds_b))

    # Source Metadata Overlap: Jaccard similarity of normalized field metadata
    if flds_a or flds_b:
        source_overlap = _jaccard_similarity(flds_a, flds_b)
    else:
        # Fallback to physical source identity similarity if no field metadata exists
        source_overlap = _jaccard_similarity(src_a, src_b)

    # 2. Production Target overlap
    tgt_a = {normalize_name(t) for t in fp_a.production_targets if t and t != "*Unknown" and "unknown" not in t.lower() and normalize_name(t)}
    tgt_b = {normalize_name(t) for t in fp_b.production_targets if t and t != "*Unknown" and "unknown" not in t.lower() and normalize_name(t)}
    target_id_overlap = _jaccard_similarity(tgt_a, tgt_b)
    shared_targets = sorted(list(tgt_a & tgt_b))
    distinct_targets_a = sorted(list(tgt_a - tgt_b))
    distinct_targets_b = sorted(list(tgt_b - tgt_a))

    # 3. Output Schema similarity
    all_cols_a = set()
    for cols in fp_a.output_schemas.values():
        for c in cols:
            if c and c != "*Unknown":
                all_cols_a.add(normalize_field_name(c))
    all_cols_b = set()
    for cols in fp_b.output_schemas.values():
        for c in cols:
            if c and c != "*Unknown":
                all_cols_b.add(normalize_field_name(c))
    all_cols_a.discard("")
    all_cols_b.discard("")

    if all_cols_a and all_cols_b:
        schema_similarity = _jaccard_similarity(all_cols_a, all_cols_b)
        schema_diffs = sorted(list((all_cols_a - all_cols_b) | (all_cols_b - all_cols_a)))
    elif not all_cols_a and not all_cols_b:
        schema_similarity = 1.0 if target_id_overlap > 0.8 else 0.5
        schema_diffs = []
    else:
        schema_similarity = 0.2
        schema_diffs = ["One workflow lacks schema definition"]

    # Target overlap reflects combined target identity and output schema overlap
    target_overlap = max(target_id_overlap, schema_similarity) if (tgt_a or tgt_b or all_cols_a or all_cols_b) else target_id_overlap

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
        shared_source_fields=shared_source_fields,
        shared_targets=shared_targets,
        dependency_status=dep_status,
        dependency_notes=dep_notes,
    )

    freq_a = (getattr(fp_a, "frequency", "Not documented") or "Not documented").strip()
    freq_b = (getattr(fp_b, "frequency", "Not documented") or "Not documented").strip()
    is_same_freq = bool(freq_a and freq_b and freq_a.lower() == freq_b.lower() and freq_a.lower() != "not documented")
    frequency_overlap = 1.0 if is_same_freq else 0.0

    metrics = DeterministicMetrics(
        source_overlap=source_overlap,
        target_overlap=target_overlap,
        transformation_similarity=transformation_similarity,
        schema_similarity=schema_similarity,
        grain_similarity=grain_similarity,
        dag_similarity=dag_similarity,
        frequency_overlap=frequency_overlap,
    )

    # 9. Explainable Opportunity Score (0 - 100)
    target_schema_score = (target_overlap * 0.6) + (schema_similarity * 0.4)
    opp_score = (
        (transformation_similarity * 35.0)
        + (source_overlap * 25.0)
        + (target_schema_score * 20.0)
        + (dag_similarity * 10.0)
        + ((1.0 if shared_sources or shared_source_fields or shared_targets else 0.0) * 10.0)
    )
    opp_score = max(0.0, min(100.0, opp_score))

    # 10. Evidence Confidence (based on evidence quality/completeness)
    if all_cols_a and all_cols_b and (fp_a.sources or fp_b.sources or flds_a or flds_b):
        confidence = "HIGH"
    elif fp_a.sources or fp_b.sources or flds_a or flds_b:
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
        shared_source_fields=shared_source_fields,
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
# 3. Deterministic Candidate Detection & Consolidation Rules
# ---------------------------------------------------------------------------
class ConsolidationRules:
    """Exact auditable rule descriptors for pairwise workflow consolidation."""
    RULE_DATA_SUBSUMPTION = "Directional data-superset subsumption with compatible processing"
    RULE_A = "100% source overlap + at least one Low complexity + same frequency"
    RULE_B = "Different outputs + at least one Low complexity + same frequency"
    RULE_C = "Different outputs + both Medium/High complexity — do not merge"
    RULE_D = "Logic can be incorporated while preserving existing result"
    RULE_DEFAULT = "No consolidation criteria met — do not merge"


def evaluate_directional_data_subsumption(
    source_fp: WorkflowFingerprint,
    target_fp: WorkflowFingerprint,
    comp: WorkflowComparisonEvidence,
) -> tuple[bool, Optional[DataSubsumptionEvidence]]:
    """Deterministically evaluate whether source_fp can be consolidated INTO target_fp.

    Direction: source_fp (absorbed) -> target_fp (retaining/superset).

    Two-layer evidence gates:
    1. Layer 1 (Data Sufficiency): target_fp must possess 100% of the fields required
       by source_fp (0 missing fields, 100% coverage).
    2. Layer 2 (Processing Substitutability): target_fp must possess compatible processing
       capabilities for all operations in source_fp, output semantics must be preserved or
       source is inspection-sink-only, with zero lost unique functionality and no blocking consumers.
    """
    # 1. Field Analysis
    req_a = set(source_fp.required_columns)
    if not req_a:
        req_a = set(source_fp.canonical_columns.keys())

    # Strip Left_/Right_ prefixes if present
    req_a_expanded = set(req_a)
    for f in req_a:
        if f.startswith("left_") or f.startswith("right_"):
            req_a_expanded.add(f[5:])
    req_a = req_a_expanded

    avail_b = set(target_fp.available_columns) | set(target_fp.canonical_columns.keys())
    for sf_list in target_fp.source_fields.values():
        for sf in sf_list:
            norm_sf = normalize_field_name(sf)
            if norm_sf:
                avail_b.add(norm_sf)
    for out_list in target_fp.output_schemas.values():
        for of in out_list:
            norm_of = normalize_field_name(of)
            if norm_of:
                avail_b.add(norm_of)

    # Expand avail_b with prefix-stripped versions
    avail_b_expanded = set(avail_b)
    for f in avail_b:
        if f.startswith("left_") or f.startswith("right_"):
            avail_b_expanded.add(f[5:])
    avail_b = avail_b_expanded

    # Check if target produces datasets consumed by source
    norm_source_inputs = {normalize_name(s) for s in source_fp.sources if s and s != "*Unknown"}
    norm_target_outputs = {normalize_name(t) for t in target_fp.production_targets if t and t != "*Unknown"}
    norm_target_inputs = {normalize_name(s) for s in target_fp.sources if s and s != "*Unknown"}

    is_target_producing_source_inputs = bool(norm_source_inputs & norm_target_outputs)

    shared_required = sorted(list(req_a & avail_b))
    missing_fields = sorted(list(req_a - avail_b))

    # If target produces the source's input files, any field in source input is guaranteed to be generated by target
    if is_target_producing_source_inputs and missing_fields:
        resolved_missing = []
        for mf in missing_fields:
            col_ev = source_fp.canonical_columns.get(mf)
            if col_ev and (
                normalize_name(col_ev.source_dataset) in norm_target_outputs
                or any(normalize_name(col_ev.source_dataset) in to for to in norm_target_outputs)
            ):
                shared_required.append(mf)
            else:
                resolved_missing.append(mf)
        missing_fields = resolved_missing
        shared_required = sorted(list(set(shared_required)))

    coverage_pct = (len(shared_required) / len(req_a)) if req_a else 1.0
    additional_in_target = sorted(list(avail_b - req_a))

    # Build field provenance map
    field_provenance_map: dict[str, ColumnEvidence] = {}
    for f in shared_required:
        if f in target_fp.canonical_columns:
            field_provenance_map[f] = target_fp.canonical_columns[f]
        elif f in source_fp.canonical_columns:
            src_ev = source_fp.canonical_columns[f]
            field_provenance_map[f] = ColumnEvidence(
                original_name=src_ev.original_name,
                normalized_name=src_ev.normalized_name,
                source_dataset=src_ev.source_dataset,
                source_tool_id=src_ev.source_tool_id,
                source_tool_type=src_ev.source_tool_type,
                provenance=f"Supplied via {target_fp.workflow_name} data pipeline / {src_ev.source_dataset}",
                sample_values=src_ev.sample_values,
                is_required=True,
            )
        else:
            field_provenance_map[f] = ColumnEvidence(
                original_name=f,
                normalized_name=f,
                source_dataset=target_fp.workflow_name,
                provenance=f"Available in {target_fp.workflow_name}",
                is_required=True,
            )

    # 2. Sample Data Matches
    sample_data_matches: list[dict[str, Any]] = []
    for s_ev in source_fp.sample_data_evidence:
        sample_data_matches.append({
            "field": s_ev.get("field"),
            "source_workflow": source_fp.workflow_name,
            "source_samples": s_ev.get("samples", []),
            "row_count": s_ev.get("row_count", 0),
            "status": "MATCHED" if s_ev.get("normalized") in avail_b else "NOT_FOUND",
        })
    for t_ev in target_fp.sample_data_evidence:
        if t_ev.get("normalized") in req_a:
            sample_data_matches.append({
                "field": t_ev.get("field"),
                "source_workflow": target_fp.workflow_name,
                "source_samples": t_ev.get("samples", []),
                "row_count": t_ev.get("row_count", 0),
                "status": "AVAILABLE_IN_TARGET",
            })

    # 3. Processing Substitutability Matrix
    matrix: list[dict[str, Any]] = []
    all_ops_supported = True

    target_tool_types = set(target_fp.tool_types)
    target_ops = target_fp.operations_summary

    for op in source_fp.operations_summary:
        ttype = op.get("tool_type", "")
        op_text = op.get("operation", "")
        tid = op.get("tool_id", "")

        status = "UNSUPPORTED"
        target_equiv = "None"
        target_tid = "N/A"
        notes = ""

        if ttype == "Union":
            if "Union" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Union combiner in target pipeline"
                notes = "Target workflow already incorporates multi-stream Union consolidation."
            else:
                status = "UNSUPPORTED"
                notes = "Target lacks Union multi-stream combiner."
                all_ops_supported = False

        elif ttype == "Unique":
            u_fields = op.get("fields", [])
            norm_u_fields = {normalize_field_name(f) for f in u_fields}
            matching_target_unique = [
                top for top in target_ops
                if top.get("tool_type") == "Unique"
                and any(normalize_field_name(f) in norm_u_fields for f in top.get("fields", []))
            ]
            if matching_target_unique:
                status = "SUPPORTED"
                target_equiv = f"Unique deduplication on {', '.join(matching_target_unique[0].get('fields', []))}"
                target_tid = matching_target_unique[0].get("tool_id", "")
                notes = "Target workflow already executes exact deduplication on matching key."
            elif "Unique" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Unique tool in target pipeline"
                notes = "Target workflow has deduplication capability."
            else:
                status = "UNSUPPORTED"
                notes = "Target lacks deduplication tool."
                all_ops_supported = False

        elif ttype == "Join":
            matching_target_join = [
                top for top in target_ops
                if top.get("tool_type") == "Join"
            ]
            if matching_target_join:
                status = "SUPPORTED"
                target_equiv = f"Join in target pipeline ({matching_target_join[0].get('operation', 'Join')})"
                target_tid = matching_target_join[0].get("tool_id", "")
                notes = "Target workflow contains compatible join capability."
            elif "Join" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Join tool in target pipeline"
                notes = "Target workflow possesses join capability."
            elif all(normalize_field_name(k) in avail_b for k in op.get("keys", [])):
                status = "SUPPORTED"
                target_equiv = "Pre-joined relation in target stream"
                notes = "Target workflow already contains all joined fields in its schema."
            else:
                status = "UNSUPPORTED"
                notes = "Target lacks join capability for required relational stream."
                all_ops_supported = False

        elif ttype == "Filter":
            if "Filter" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Filter tool in target pipeline"
                notes = "Target workflow possesses filtering capability."
            else:
                status = "UNSUPPORTED"
                all_ops_supported = False

        elif ttype == "Formula":
            target_field = op.get("target_field", "")
            norm_tf = normalize_field_name(target_field)
            if norm_tf in avail_b:
                status = "SUPPORTED"
                target_equiv = f"Calculated field [{target_field}]"
                notes = "Target workflow already derives and provides this calculated attribute."
            elif "Formula" in target_tool_types or "MultiRowFormula" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Formula engine in target pipeline"
                notes = "Target workflow has formula calculation capability."
            else:
                status = "UNSUPPORTED"
                all_ops_supported = False

        elif ttype == "Summarize":
            if "Summarize" in target_tool_types:
                status = "SUPPORTED"
                target_equiv = "Summarize aggregation tool in target pipeline"
                notes = "Target workflow has aggregation capability."
            else:
                status = "UNSUPPORTED"
                all_ops_supported = False

        elif ttype in ("TextToColumns", "RegEx"):
            if ttype in target_tool_types:
                status = "SUPPORTED"
                target_equiv = f"{ttype} in target workflow"
                notes = f"Target contains equivalent {ttype} parsing tool."
            else:
                status = "SUPPORTED"
                target_equiv = "Parsed schema fields available"
                notes = "Target already contains parsed business attributes in its schema."

        elif ttype == "Sort":
            status = "SUPPORTED"
            target_equiv = "Sort tool in target pipeline" if "Sort" in target_tool_types else "Relational ordering"
            notes = "Sorting can be maintained in target pipeline."

        else:
            if ttype in target_tool_types:
                status = "SUPPORTED"
                target_equiv = f"{ttype} in target workflow"
                notes = f"Target contains equivalent {ttype} tool."
            else:
                status = "SUPPORTED"
                target_equiv = "Implicit pass-through"
                notes = f"Operation [{ttype}] can be consolidated without loss."

        matrix.append({
            "source_tool_id": tid,
            "source_tool_type": ttype,
            "source_operation": op_text,
            "target_equivalent": target_equiv,
            "target_tool_id": target_tid,
            "status": status,
            "notes": notes,
        })

    processing_compatibility = "SUPPORTED" if all_ops_supported else "UNSUPPORTED"

    # 4. Output Compatibility
    if len(source_fp.production_targets) == 0 and len(source_fp.inspection_sinks) > 0:
        output_compatibility = "INSPECTION_SINK_ONLY"
    elif set(source_fp.production_targets) == set(target_fp.production_targets):
        output_compatibility = "IDENTICAL"
    elif set(source_fp.production_targets).issubset(set(target_fp.production_targets)):
        output_compatibility = "COMPATIBLE"
    elif is_target_producing_source_inputs:
        output_compatibility = "COMPATIBLE"
    elif len(source_fp.production_targets) > 0 and len(missing_fields) == 0:
        output_compatibility = "COMPATIBLE"
    else:
        output_compatibility = "INCOMPATIBLE"

    # 5. Unique Functionality Check
    unresolved_unique_details: list[str] = []
    if source_fp.has_python and not target_fp.has_python:
        unresolved_unique_details.append(f"{source_fp.workflow_name} contains custom Python code not present in {target_fp.workflow_name}")
    if source_fp.has_r and not target_fp.has_r:
        unresolved_unique_details.append(f"{source_fp.workflow_name} contains R statistical scripts not present in {target_fp.workflow_name}")
    if source_fp.has_macros and not target_fp.has_macros:
        unresolved_unique_details.append(f"{source_fp.workflow_name} contains macro assets not present in {target_fp.workflow_name}")

    has_unresolved_unique = len(unresolved_unique_details) > 0

    # 6. Downstream Consumers Check
    has_blocking_consumers = len(source_fp.downstream_consumers) > 0

    # 7. Subsumption Gate Qualification (Mandatory: Source Metadata Overlap > 60%)
    is_subsumed = bool(
        comp.metrics.source_overlap > 0.60
        and len(missing_fields) == 0
        and coverage_pct == 1.0
        and len(req_a) > 0
        and processing_compatibility == "SUPPORTED"
        and output_compatibility in ("INSPECTION_SINK_ONLY", "IDENTICAL", "COMPATIBLE")
        and not has_unresolved_unique
        and not has_blocking_consumers
    )

    direction_statement = f"{source_fp.workflow_name} can be consolidated into {target_fp.workflow_name}"
    recommendation_summary = (
        f"{target_fp.workflow_name} contains 100% of the required data/fields ({len(shared_required)} fields) "
        f"and possesses compatible processing capability to reproduce {source_fp.workflow_name}'s functionality "
        f"with zero lost unique logic."
    )

    evidence = DataSubsumptionEvidence(
        source_workflow_id=source_fp.workflow_id,
        source_workflow_name=source_fp.workflow_name,
        target_workflow_id=target_fp.workflow_id,
        target_workflow_name=target_fp.workflow_name,
        data_coverage_pct=coverage_pct,
        missing_fields_count=len(missing_fields),
        missing_fields=missing_fields,
        shared_required_fields=shared_required,
        additional_fields_in_target=additional_in_target,
        field_provenance_map=field_provenance_map,
        sample_data_matches=sample_data_matches,
        processing_substitutability_matrix=matrix,
        processing_compatibility=processing_compatibility,
        output_compatibility=output_compatibility,
        has_unresolved_unique_functionality=has_unresolved_unique,
        unresolved_unique_details=unresolved_unique_details,
        direction_statement=direction_statement,
        recommendation_summary=recommendation_summary,
    )

    return is_subsumed, evidence


def evaluate_consolidation_rules(
    fp_a: WorkflowFingerprint,
    fp_b: WorkflowFingerprint,
    comp: WorkflowComparisonEvidence,
) -> ConsolidationDecision:
    """Evaluate pairwise deterministic consolidation/merge rules from canonical evidence.

    Order of evaluation:
    1. Obtain deterministic Source Metadata Overlap: comp.metrics.source_overlap
    2. Apply Hard Eligibility Gate: Source Metadata Overlap > 60% (> 0.60).
       If <= 60%, STOP CONSOLIDATION EVALUATION -> DO NOT MERGE.
    3. Evaluate Directional Data Subsumption Gates.
    4. Evaluate Functional Subsumption / Logic Preservation (Rule D).
    5. Evaluate Identical Sources & Low Complexity (Rule A).
    6. Evaluate Incompatible Outputs / Medium-High Complexity (Rule C).
    7. Default fallback: DO NOT MERGE.
    """
    source_overlap_pct = comp.metrics.source_overlap

    # 1. Physical normalized sources (exclude *Unknown and empty)
    src_a = {normalize_name(s) for s in fp_a.sources if s and s != "*Unknown" and "unknown" not in s.lower() and normalize_name(s)}
    src_b = {normalize_name(s) for s in fp_b.sources if s and s != "*Unknown" and "unknown" not in s.lower() and normalize_name(s)}
    is_source_100_pct = bool(src_a and src_b and src_a == src_b)

    # 2. Physical normalized targets (exclude *Unknown and empty)
    tgt_a = {normalize_name(t) for t in fp_a.production_targets if t and t != "*Unknown" and "unknown" not in t.lower() and normalize_name(t)}
    tgt_b = {normalize_name(t) for t in fp_b.production_targets if t and t != "*Unknown" and "unknown" not in t.lower() and normalize_name(t)}
    different_outputs = bool((tgt_a != tgt_b) and (tgt_a or tgt_b))
    if tgt_a and tgt_b and tgt_a == tgt_b:
        output_rel = "IDENTICAL"
    elif tgt_a and tgt_b and not (tgt_a & tgt_b):
        output_rel = "DIFFERENT"
    elif tgt_a & tgt_b:
        output_rel = "OVERLAPPING"
    else:
        output_rel = "DIFFERENT" if (tgt_a or tgt_b) else "NONE"

    # 3. Complexity
    comp_a = (getattr(fp_a, "complexity_level", "LOW") or "LOW").upper()
    comp_b = (getattr(fp_b, "complexity_level", "LOW") or "LOW").upper()
    has_low_complexity = (comp_a == "LOW" or comp_b == "LOW")
    both_medium_or_high = (comp_a in ("MEDIUM", "HIGH") and comp_b in ("MEDIUM", "HIGH"))

    # 4. Frequency
    freq_a = (getattr(fp_a, "frequency", "Not documented") or "Not documented").strip()
    freq_b = (getattr(fp_b, "frequency", "Not documented") or "Not documented").strip()
    is_same_frequency = bool(freq_a and freq_b and freq_a.lower() == freq_b.lower())

    # Build concise auditable evidence
    if is_source_100_pct:
        if comp.shared_sources:
            source_desc = f"100% identical source files ({len(comp.shared_sources)} datasets: {', '.join(sorted(comp.shared_sources))})"
        elif comp.shared_source_fields:
            source_desc = f"100% source metadata overlap ({len(comp.shared_source_fields)} matching fields)"
        else:
            source_desc = "100% source metadata overlap"
    elif comp.shared_source_fields:
        source_desc = f"{round(source_overlap_pct * 100)}% source metadata overlap ({len(comp.shared_source_fields)} matching fields)"
    elif comp.shared_sources:
        source_desc = f"{round(source_overlap_pct * 100)}% source overlap (shared: {', '.join(comp.shared_sources)})"
    else:
        source_desc = f"{round(source_overlap_pct * 100)}% source overlap"

    target_desc = (
        f"Different output destinations ({fp_a.workflow_name}: {', '.join(sorted(tgt_a)) or 'None'} vs {fp_b.workflow_name}: {', '.join(sorted(tgt_b)) or 'None'})"
        if different_outputs
        else (f"Identical production targets ({', '.join(sorted(tgt_a))})" if tgt_a else "No production targets configured")
    )
    evidence = [
        f"Source overlap: {source_desc}",
        f"Production targets: {target_desc}",
        f"Complexity: {fp_a.workflow_name} is {comp_a}, {fp_b.workflow_name} is {comp_b}",
        f"Frequency: {fp_a.workflow_name} is '{freq_a}', {fp_b.workflow_name} is '{freq_b}' ({'Same frequency' if is_same_frequency else 'Different frequency'})",
    ]

    # STEP 2: HARD GATE — Source Metadata Overlap must be strictly > 60% (> 0.60) for CONSOLIDATE / MERGE
    if source_overlap_pct <= 0.60:
        return ConsolidationDecision(
            recommendation="DO NOT MERGE",
            matched_rule=ConsolidationRules.RULE_DEFAULT,
            reason=f"Source metadata overlap ({round(source_overlap_pct * 100)}%) does not satisfy the mandatory >60% threshold required for workflow consolidation.",
            evidence=evidence,
            source_overlap_pct=source_overlap_pct,
            is_source_100_pct=is_source_100_pct,
            output_relationship=output_rel,
            complexity_a=comp_a,
            complexity_b=comp_b,
            frequency_a=freq_a,
            frequency_b=freq_b,
            is_same_frequency=is_same_frequency,
            logic_preservable=False,
            merge_direction=None,
        )

    # STEP 3: Directional Data Subsumption Gates (>60% source overlap already verified)
    subsumes_a_in_b, ev_a_in_b = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    if subsumes_a_in_b and ev_a_in_b is not None:
        subsumption_evidence = [
            f"Data Sufficiency: 100% field coverage ({len(ev_a_in_b.shared_required_fields)} shared required fields, 0 missing in {fp_b.workflow_name})",
            f"Processing Substitutability: {ev_a_in_b.processing_compatibility} across all {fp_a.workflow_name} operations",
            f"Output Semantics: {ev_a_in_b.output_compatibility} ({fp_a.workflow_name} inspection sinks fully preservable)",
            f"Direction: {ev_a_in_b.direction_statement}",
        ]
        return ConsolidationDecision(
            recommendation="MERGE",
            matched_rule=ConsolidationRules.RULE_DATA_SUBSUMPTION,
            reason=ev_a_in_b.recommendation_summary,
            evidence=subsumption_evidence,
            source_overlap_pct=comp.metrics.source_overlap,
            is_source_100_pct=bool(comp.metrics.source_overlap >= 0.99),
            output_relationship=ev_a_in_b.output_compatibility,
            complexity_a=(fp_a.complexity_level or "LOW").upper(),
            complexity_b=(fp_b.complexity_level or "LOW").upper(),
            frequency_a=fp_a.frequency,
            frequency_b=fp_b.frequency,
            is_same_frequency=bool(fp_a.frequency and fp_b.frequency and fp_a.frequency.lower() == fp_b.frequency.lower()),
            logic_preservable=True,
            merge_direction=ev_a_in_b.direction_statement,
            data_subsumption_evidence=ev_a_in_b,
        )

    subsumes_b_in_a, ev_b_in_a = evaluate_directional_data_subsumption(fp_b, fp_a, comp)
    if subsumes_b_in_a and ev_b_in_a is not None:
        subsumption_evidence = [
            f"Data Sufficiency: 100% field coverage ({len(ev_b_in_a.shared_required_fields)} shared required fields, 0 missing in {fp_a.workflow_name})",
            f"Processing Substitutability: {ev_b_in_a.processing_compatibility} across all {fp_b.workflow_name} operations",
            f"Output Semantics: {ev_b_in_a.output_compatibility} ({fp_b.workflow_name} inspection sinks fully preservable)",
            f"Direction: {ev_b_in_a.direction_statement}",
        ]
        return ConsolidationDecision(
            recommendation="MERGE",
            matched_rule=ConsolidationRules.RULE_DATA_SUBSUMPTION,
            reason=ev_b_in_a.recommendation_summary,
            evidence=subsumption_evidence,
            source_overlap_pct=comp.metrics.source_overlap,
            is_source_100_pct=bool(comp.metrics.source_overlap >= 0.99),
            output_relationship=ev_b_in_a.output_compatibility,
            complexity_a=(fp_a.complexity_level or "LOW").upper(),
            complexity_b=(fp_b.complexity_level or "LOW").upper(),
            frequency_a=fp_a.frequency,
            frequency_b=fp_b.frequency,
            is_same_frequency=bool(fp_a.frequency and fp_b.frequency and fp_a.frequency.lower() == fp_b.frequency.lower()),
            logic_preservable=True,
            merge_direction=ev_b_in_a.direction_statement,
            data_subsumption_evidence=ev_b_in_a,
        )

    # 5. Logic / Result Preservation (Rule D)
    sig_a = {s for s in fp_a.transformation_signatures if is_meaningful_evidence(s)}
    sig_b = {s for s in fp_b.transformation_signatures if is_meaningful_evidence(s)}

    logic_preservable = False
    preservation_reason = ""
    merge_direction: Optional[str] = None

    if sig_b and sig_b.issubset(sig_a) and tgt_b and tgt_b.issubset(tgt_a) and len(sig_b) >= 2:
        logic_preservable = True
        preservation_reason = f"Functional subsumption: {fp_a.workflow_name} already executes all transformations and generates targets of {fp_b.workflow_name}."
        merge_direction = f"{fp_a.workflow_name} absorbs {fp_b.workflow_name}"
    elif sig_a and sig_a.issubset(sig_b) and tgt_a and tgt_a.issubset(tgt_b) and len(sig_a) >= 2:
        logic_preservable = True
        preservation_reason = f"Functional subsumption: {fp_b.workflow_name} already executes all transformations and generates targets of {fp_a.workflow_name}."
        merge_direction = f"{fp_b.workflow_name} absorbs {fp_a.workflow_name}"

    # Determine merge direction when not set by Rule D and recommendation is MERGE
    if not merge_direction and has_low_complexity:
        if comp_a != "LOW" and comp_b == "LOW":
            merge_direction = f"{fp_a.workflow_name} absorbs {fp_b.workflow_name}"
        elif comp_b != "LOW" and comp_a == "LOW":
            merge_direction = f"{fp_b.workflow_name} absorbs {fp_a.workflow_name}"
        elif fp_a.node_count > fp_b.node_count:
            merge_direction = f"{fp_a.workflow_name} absorbs {fp_b.workflow_name}"
        elif fp_b.node_count > fp_a.node_count:
            merge_direction = f"{fp_b.workflow_name} absorbs {fp_a.workflow_name}"

    if logic_preservable:
        evidence.append(f"Logic preservation: {preservation_reason}")

    # Decision evaluation hierarchy:
    # 1. Rule D: Logic can be incorporated while preserving existing result
    if logic_preservable:
        return ConsolidationDecision(
            recommendation="MERGE",
            matched_rule=ConsolidationRules.RULE_D,
            reason=f"Workflow logic can be unified while preserving existing production deliverables ({preservation_reason}).",
            evidence=evidence,
            source_overlap_pct=source_overlap_pct,
            is_source_100_pct=is_source_100_pct,
            output_relationship=output_rel,
            complexity_a=comp_a,
            complexity_b=comp_b,
            frequency_a=freq_a,
            frequency_b=freq_b,
            is_same_frequency=is_same_frequency,
            logic_preservable=True,
            merge_direction=merge_direction,
        )

    # 2. Rule A: 100% source overlap + at least one Low complexity + same frequency
    if is_source_100_pct and has_low_complexity and is_same_frequency:
        return ConsolidationDecision(
            recommendation="MERGE",
            matched_rule=ConsolidationRules.RULE_A,
            reason="Both workflows consume identical source inputs on the same operational schedule with at least one Low complexity workflow, qualifying for consolidation.",
            evidence=evidence,
            source_overlap_pct=source_overlap_pct,
            is_source_100_pct=True,
            output_relationship=output_rel,
            complexity_a=comp_a,
            complexity_b=comp_b,
            frequency_a=freq_a,
            frequency_b=freq_b,
            is_same_frequency=True,
            logic_preservable=False,
            merge_direction=merge_direction,
        )

    # 4. Rule C: Different outputs + both Medium/High complexity
    if different_outputs and both_medium_or_high:
        return ConsolidationDecision(
            recommendation="DO NOT MERGE",
            matched_rule=ConsolidationRules.RULE_C,
            reason="Both workflows have Medium or High complexity and produce different output targets; combining them would introduce unnecessary architectural coupling.",
            evidence=evidence,
            source_overlap_pct=source_overlap_pct,
            is_source_100_pct=is_source_100_pct,
            output_relationship="DIFFERENT",
            complexity_a=comp_a,
            complexity_b=comp_b,
            frequency_a=freq_a,
            frequency_b=freq_b,
            is_same_frequency=is_same_frequency,
            logic_preservable=False,
            merge_direction=None,
        )

    # 5. Default fallback
    return ConsolidationDecision(
        recommendation="DO NOT MERGE",
        matched_rule=ConsolidationRules.RULE_DEFAULT,
        reason="Workflows do not satisfy consolidation merge criteria (lack of common source/logic evidence, incompatible complexity, or differing execution schedules).",
        evidence=evidence,
        source_overlap_pct=source_overlap_pct,
        is_source_100_pct=is_source_100_pct,
        output_relationship=output_rel,
        complexity_a=comp_a,
        complexity_b=comp_b,
        frequency_a=freq_a,
        frequency_b=freq_b,
        is_same_frequency=is_same_frequency,
        logic_preservable=False,
        merge_direction=None,
    )


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

    # Evaluate exact consolidation rules (including Rule DATA SUBSUMPTION, A, B, C, D)
    consolidation_decision = evaluate_consolidation_rules(fp_a, fp_b, comp)

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
    # ONLY qualify as CONSOLIDATE if exact deterministic merge rules evaluated to MERGE and source overlap > 60%
    can_consolidate = (
        consolidation_decision.recommendation == "MERGE"
        and m.source_overlap > 0.60
    )

    # Safety Gate 3: Check SHARED_LOGIC
    can_shared_logic = (
        m.transformation_similarity >= t.SHARED_LOGIC_SIMILARITY_MIN
        or (len(comp.shared_logic) >= 2 and comp.opportunity_score >= 30.0)
    )

    # Safety Gate 4: Check REVIEW
    has_any_overlap = bool(
        m.source_overlap > 0.0
        or m.transformation_similarity > 0.0
        or m.target_overlap > 0.0
        or comp.shared_sources
        or comp.shared_targets
        or comp.shared_logic
        or consolidation_decision.data_subsumption_evidence is not None
    )
    can_review = (
        has_any_overlap
        and (
            comp.opportunity_score >= t.MIN_SURFACE_SCORE
            or m.source_overlap >= t.REVIEW_OVERLAP_MIN
            or (len(comp.shared_sources) > 0 and m.transformation_similarity >= 0.20)
            or consolidation_decision.data_subsumption_evidence is not None
        )
    )

    # Determine recommendation and admissible bounds
    original_type = ""
    if can_retire:
        recommendation_type = "RETIRE"
        admissible = ["RETIRE", "RETIRE_CANDIDATE", "REVIEW"]
    elif can_consolidate:
        recommendation_type = "CONSOLIDATE"
        admissible = ["CONSOLIDATE"]
    elif can_shared_logic:
        recommendation_type = "SHARED_LOGIC"
        admissible = ["SHARED_LOGIC"]
    elif can_review:
        recommendation_type = "RETIRE"
        admissible = ["RETIRE", "RETIRE_CANDIDATE", "REVIEW"]
        original_type = "REVIEW"
    else:
        # NO_ACTION: Return None so unrelated workflows are never surfaced in the UI!
        return None

    # Deterministic Reasoning & Proposed Strategy
    if consolidation_decision.data_subsumption_evidence is not None:
        dse = consolidation_decision.data_subsumption_evidence
        if dse.data_coverage_pct == 1.0 and consolidation_decision.recommendation == "MERGE":
            m = DeterministicMetrics(
                source_overlap=1.0,
                target_overlap=m.target_overlap,
                transformation_similarity=m.transformation_similarity,
                schema_similarity=m.schema_similarity,
                grain_similarity=m.grain_similarity,
                dag_similarity=m.dag_similarity,
                frequency_overlap=m.frequency_overlap,
            )
        reasoning = (
            f"{dse.target_workflow_name} processes the complete dataset required by {dse.source_workflow_name} "
            f"({len(dse.shared_required_fields)} input fields with 100% data sufficiency) and shares core operational processing. "
            f"Merging the workflows eliminates redundant ingestion and staging while fully preserving downstream business outputs."
        )
        proposed_strategy = (
            f"Consolidate {dse.source_workflow_name} into {dse.target_workflow_name}. Redirect downstream operational "
            f"consumers to {dse.target_workflow_name} and decommission {dse.source_workflow_name} following validation."
        )
        evidence_list = [
            f"Data Sufficiency: 100% field coverage ({len(dse.shared_required_fields)} fields, 0 missing in {dse.target_workflow_name})",
            f"Processing Substitutability: {dse.processing_compatibility} across all operations in {dse.source_workflow_name}",
            f"Output Semantics: {dse.output_compatibility} ({dse.source_workflow_name} output requirements fully preserved)",
            f"Direction: {dse.direction_statement}",
        ]
        validation_reqs = [
            f"Verify all consumers of {dse.source_workflow_name} are redirected to {dse.target_workflow_name}",
            f"Confirm {dse.target_workflow_name} scheduled execution covers the operational window of {dse.source_workflow_name}",
            f"Inspect sample outputs from {dse.target_workflow_name} to confirm field schema parity",
        ]
    elif recommendation_type in ("RETIRE", "RETIRE_CANDIDATE") and not original_type:
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
        if comp.shared_sources:
            source_desc_str = f"consume overlapping source datasets ({', '.join(comp.shared_sources)})"
        elif consolidation_decision.is_source_100_pct:
            source_desc_str = "consume identical source datasets"
        else:
            source_desc_str = f"operate on distinct source datasets ({len(fp_a.sources)} in {fp_a.workflow_name}, {len(fp_b.sources)} in {fp_b.workflow_name})"

        if m.transformation_similarity > 0:
            logic_desc_str = f"share {round(m.transformation_similarity * 100)}% core operational logic"
        else:
            logic_desc_str = "execute distinct transformation pipelines"

        if comp.distinct_targets_a or comp.distinct_targets_b:
            target_desc_str = f"distinct production outputs ({', '.join(comp.distinct_targets_a + comp.distinct_targets_b)})"
        elif comp.shared_targets:
            target_desc_str = f"shared targets ({', '.join(comp.shared_targets)})"
        else:
            target_desc_str = "configured output endpoints"

        reasoning = (
            f"Both workflows {source_desc_str} and {logic_desc_str}, while generating {target_desc_str}. "
            f"Consolidated execution would streamline maintenance and pipeline governance without compromising deliverables."
        )
        proposed_strategy = (
            "Centralize the common ingestion, filtering, and cleansing pipeline into a unified shared processing layer, "
            "retaining distinct downstream branches for unique analytical outputs."
        )
        if comp.shared_source_fields:
            src_str = f"{round(m.source_overlap * 100)}% source metadata overlap ({len(comp.shared_source_fields)} matching fields)"
        elif comp.shared_sources:
            src_str = f"{round(m.source_overlap * 100)}% source overlap ({len(comp.shared_sources)} shared inputs)"
        else:
            src_str = f"{round(m.source_overlap * 100)}% source overlap"

        evidence_list = [
            src_str,
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
        if comp.shared_source_fields:
            src_rev_str = f"{round(m.source_overlap * 100)}% source metadata overlap"
        elif comp.shared_sources:
            src_rev_str = f"{round(m.source_overlap * 100)}% source overlap"
        else:
            src_rev_str = f"{round(m.source_overlap * 100)}% source overlap"

        evidence_list = [
            f"Opportunity score: {round(comp.opportunity_score, 1)}/100",
            f"{src_rev_str}, {round(m.transformation_similarity * 100)}% logic similarity",
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
        consolidation_decision=consolidation_decision,
        data_subsumption_evidence=consolidation_decision.data_subsumption_evidence,
        sources_by_workflow={
            fp_a.workflow_name: fp_a.sources,
            fp_b.workflow_name: fp_b.sources,
        },
        source_fields_by_workflow={
            fp_a.workflow_name: fp_a.source_fields,
            fp_b.workflow_name: fp_b.source_fields,
        },
        transformations_by_workflow={
            fp_a.workflow_name: [s for s in fp_a.transformation_signatures if is_meaningful_evidence(s)],
            fp_b.workflow_name: [s for s in fp_b.transformation_signatures if is_meaningful_evidence(s)],
        },
        frequencies_by_workflow={
            fp_a.workflow_name: fp_a.frequency,
            fp_b.workflow_name: fp_b.frequency,
        },
        original_recommendation_type=original_type or recommendation_type,
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
        "3. Provide business-friendly, professional explanations of why the logic overlaps and what strategy to follow. "
        "Explain data similarity, process overlap, data sufficiency, and business deliverable preservation in clear executive language without raw similarity metric decimals.\n"
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
            if candidate.recommendation_type == "CONSOLIDATE" and (
                (candidate.consolidation_decision and candidate.consolidation_decision.recommendation == "MERGE")
                or candidate.data_subsumption_evidence is not None
            ):
                # Deterministic MERGE classification is strictly immutable and cannot be overridden by LLM
                candidate.recommendation_type = "CONSOLIDATE"
            elif rec in candidate.admissible_recommendations:
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
                        recommendation_type="RETIRE",
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
                        admissible_recommendations=["RETIRE", "RETIRE_CANDIDATE", "REVIEW"],
                        llm_enrichment_status="DETERMINISTIC_BASELINE",
                        original_recommendation_type="REVIEW",
                    )
                )

    # Sort candidates by opportunity score descending
    candidates.sort(key=lambda c: c.opportunity_score, reverse=True)

    # 5. Compute canonical workflow-level partition: Retire ∪ Consolidate ∪ Keep
    # Every analysed workflow belongs to exactly one final bucket.
    workflow_classifications: dict[str, str] = {}

    consolidate_candidates = [
        c for c in candidates
        if c.recommendation_type == "CONSOLIDATE"
        and (c.consolidation_decision is not None and c.consolidation_decision.recommendation == "MERGE")
        and (c.deterministic_metrics.source_overlap > 0.60)
    ]
    retire_candidates = [
        c for c in candidates
        if c.recommendation_type in ("RETIRE", "RETIRE_CANDIDATE", "REVIEW")
    ]

    for summary in portfolio.workflows:
        wid = summary.workflow_id

        # 1. Consolidate priority
        is_consolidated = any(wid in cand.workflow_ids for cand in consolidate_candidates)
        if is_consolidated:
            workflow_classifications[wid] = "CONSOLIDATE"
            summary.rationalisation_status = "CONSOLIDATE"
            continue

        # 2. Retire priority
        is_retired = any(wid in cand.workflow_ids for cand in retire_candidates)
        if is_retired:
            workflow_classifications[wid] = "RETIRE"
            summary.rationalisation_status = "RETIRE"
            continue

        # 3. Residual non-candidate bucket is KEEP
        workflow_classifications[wid] = "KEEP"
        summary.rationalisation_status = "KEEP"

    retire_count = sum(1 for s in workflow_classifications.values() if s == "RETIRE")
    consolidate_count = sum(1 for s in workflow_classifications.values() if s == "CONSOLIDATE")
    keep_count = sum(1 for s in workflow_classifications.values() if s == "KEEP")

    workflow_counts = {
        "RETIRE": retire_count,
        "CONSOLIDATE": consolidate_count,
        "KEEP": keep_count,
    }

    rec_counts = {
        "CONSOLIDATE": consolidate_count,
        "RETIRE": retire_count,
        "KEEP": keep_count,
        "RETIRE_CANDIDATE": retire_count,
        "SHARED_LOGIC": sum(1 for c in candidates if c.recommendation_type == "SHARED_LOGIC"),
        "REVIEW": 0,
    }

    return RationalisationAnalysis(
        portfolio_id=portfolio.portfolio_id,
        candidates=candidates,
        total_opportunities=len(candidates),
        recommendation_counts=rec_counts,
        workflow_classifications=workflow_classifications,
        workflow_counts=workflow_counts,
        analysed_workflow_count=len(portfolio.workflows),
    )
