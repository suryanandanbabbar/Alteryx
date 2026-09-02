"""Business-area classification for Alteryx workflows within a portfolio.

Core Architectural Invariants:
1. Workflow Business Purpose is the primary semantic classification signal.
2. Production output dataset/file names, table/sheet names, and output column headers provide supporting evidence.
3. Allowed Business Areas:
   - Claims & Risk
   - Legal
   - Underwriting
   - Sales & Distribution
   - UNCLASSIFIED
4. Deterministic Fallback: A tokenized domain taxonomy classifier is used whenever the LLM is
   disabled, unavailable, times out, or returns invalid/hallucinated data.
5. Count Integrity: Every workflow is assigned to exactly one valid business area.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from awa.analysis.sttm_extractor import _clean_table_name
from awa.llm.generator import LLMNarrativeGenerator, get_default_generator
from awa.llm.prompts import (
    BUSINESS_AREA_CLASSIFICATION_PROMPT_VERSION,
    BUSINESS_AREA_CLASSIFICATION_SYSTEM_PROMPT,
    PORTFOLIO_BUSINESS_AREA_CLASSIFICATION_SYSTEM_PROMPT,
    build_business_area_classification_user_prompt,
    build_portfolio_business_area_classification_user_prompt,
)
from awa.llm.schemas import NarrativeResult
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.portfolio import BusinessAreaClassification

logger = logging.getLogger(__name__)

ALLOWED_BUSINESS_AREAS: tuple[str, ...] = (
    "Claims & Risk",
    "Legal",
    "Underwriting",
    "Sales & Distribution",
)

BUSINESS_AREA_DESCRIPTIONS: dict[str, str] = {
    "Claims & Risk": (
        "Claims & Risk business area encompasses multiple workflows that collectively "
        "analyse claims performance, exposure, policy information, payments, and litigation or risk-related outcomes."
    ),
    "Sales & Distribution": (
        "Sales & Distribution business area encompasses workflows that support customer, "
        "product, sales performance, distribution, pipeline, and commercial reporting activities."
    ),
    "Legal": (
        "Legal business area encompasses workflows supporting legal operations, "
        "case-related information, regulatory analysis, legal reporting, and compliance-oriented data processing."
    ),
    "Underwriting": (
        "Underwriting business area encompasses workflows that support risk assessment, "
        "policy evaluation, underwriting decisions, pricing inputs, and portfolio analysis."
    ),
    "Other / Unclassified": (
        "These workflows could not be confidently associated with a recognised "
        "business area based on the available workflow output evidence."
    ),
}

# ---------------------------------------------------------------------------
# Domain Taxonomies for Deterministic Fallback
# ---------------------------------------------------------------------------

DOMAIN_TAXONOMY: dict[str, set[str]] = {
    "Claims & Risk": {
        "claim", "claims", "claimant", "risk", "fraud", "loss", "incident",
        "exposure", "settlement", "severity", "subrogation", "indemnity",
        "salvage", "recovery", "reserves", "incurred", "aging", "litigated",
        "catastrophe", "adjuster", "liability", "peril", "payout",
    },
    "Legal": {
        "legal", "case", "matter", "contract", "litigation", "attorney",
        "court", "compliance", "arbitration", "dispute", "counsel",
        "jurisdiction", "regulatory", "docket", "pleading", "statute",
        "lawsuit", "subpoena", "clause", "agreement", "plaintiff", "defendant",
    },
    "Underwriting": {
        "underwriting", "underwrite", "underwriter", "applicant", "eligibility",
        "coverage", "premium", "policy", "risk_class", "policy_term",
        "endorsement", "binder", "actuarial", "rating", "insured",
        "deductible", "limit", "appetite", "guideline", "reinsurance",
    },
    "Sales & Distribution": {
        "sales", "sale", "revenue", "order", "distributor", "distribution",
        "channel", "commission", "customer", "client", "territory", "quota",
        "pipeline", "broker", "agent", "gross_sales", "net_sales",
        "product_sales", "marketing", "producer", "retail", "wholesale",
    },
}


def _tokenize_text(text: Any) -> list[str]:
    """Tokenize an identifier, filename, or text string into lowercase normalized word tokens."""
    if not isinstance(text, str):
        return []
    # Strip file extensions (e.g. .xlsx, .csv, .tde, .yxdb)
    clean = re.sub(r"\.[a-zA-Z0-9]+$", "", text)
    # Split on non-alphanumeric chars and camelCase boundaries
    tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|[0-9]+", clean)
    return [t.lower() for t in tokens if len(t) > 1]


def extract_output_evidence_for_workflow(result: CanonicalAnalysisResult) -> list[dict[str, Any]]:
    """Extract strictly bounded output evidence for a workflow.

    CRITICAL: Contains ONLY output dataset/file name, table/sheet name, and output column headers.
    Must NOT contain workflow name, workflow ID, sources, tool sequence, or business summary.
    """
    outputs: list[dict[str, Any]] = []
    seen_datasets: set[str] = set()

    for tid, tool in sorted(result.workflow.tools.items()):
        # 1. Skip terminal inspection sinks (Browse/BrowseV2)
        if tool.tool_type in ("BrowseV2", "Browse"):
            continue

        # 2. Check if explicit output tool or non-browse leaf
        is_explicit_output = tool.tool_type in ("DbFileOutput", "OutputData", "Render")
        is_leaf = (
            result.graph.has_node(tid)
            and result.graph.out_degree(tid) == 0
            and tool.tool_type not in ("BrowseV2", "Browse")
        )

        if not (is_explicit_output or is_leaf):
            continue

        cfg = tool.configuration.parsed if hasattr(tool.configuration, "parsed") else (
            tool.configuration if isinstance(tool.configuration, dict) else {}
        )
        file_path = (
            cfg.get("file_path", "")
            or cfg.get("File", "")
            or cfg.get("destination_file", "")
        )

        target_name = ""
        table_or_sheet = ""
        if file_path:
            raw_path = str(file_path)
            if "|||" in raw_path:
                parts = raw_path.split("|||", 1)
                target_name = _clean_table_name(parts[0])
                table_or_sheet = parts[1].strip("`[] ")
            else:
                target_name = _clean_table_name(raw_path)
        elif result.business_summary:
            biz_outputs = {out.tool_id: out for out in result.business_summary.business_outputs}
            if tid in biz_outputs and (biz_outputs[tid].raw_destination or biz_outputs[tid].name):
                raw = biz_outputs[tid].raw_destination or biz_outputs[tid].name
                if raw and raw.lower() not in ("standard output stream", "in-memory destination"):
                    target_name = _clean_table_name(raw)

        if not target_name or "*" in target_name or target_name.lower() == "*unknown":
            if is_explicit_output:
                target_name = f"Output #{tid}"
            else:
                continue

        if target_name in seen_datasets:
            continue
        seen_datasets.add(target_name)

        # Collect output column headers for this output deliverable
        columns: list[str] = []
        seen_cols: set[str] = set()

        def add_col(c: str):
            if c and not c.startswith("*") and c.lower() != "*unknown" and c not in seen_cols:
                seen_cols.add(c)
                columns.append(c)

        # A. Columns from STTM mappings for this target dataset
        if result.sttm:
            for m in result.sttm.mappings:
                tgt = getattr(m, "target_table", None) or getattr(m, "target_dataset", None)
                if tgt and (tgt == target_name or tgt.lower() == target_name.lower()):
                    add_col(m.target_attribute)

        # B. Columns from tool's own output_fields
        if hasattr(tool, "output_fields") and tool.output_fields:
            for f in tool.output_fields:
                add_col(f.name)

        # C. Columns from upstream tools feeding this output node
        if result.graph.has_node(tid):
            for pred_tid in result.graph.predecessors(tid):
                pred_tool = result.workflow.tools.get(pred_tid)
                if pred_tool and hasattr(pred_tool, "output_fields"):
                    for f in pred_tool.output_fields:
                        add_col(f.name)

        output_entry: dict[str, Any] = {
            "dataset": target_name,
            "columns": columns,
        }
        if table_or_sheet:
            output_entry["table_or_sheet"] = table_or_sheet

        outputs.append(output_entry)

    return outputs


def classify_business_area_deterministic(
    output_evidence: list[dict[str, Any]],
    business_purpose: str = "",
) -> BusinessAreaClassification:
    """Classify workflow business area deterministically using output evidence and business purpose tokens."""
    if not output_evidence and not business_purpose:
        return BusinessAreaClassification(
            business_area="UNCLASSIFIED",
            confidence="UNCLASSIFIED",
            evidence=[],
            classification_source="deterministic_fallback",
            secondary_business_areas=[],
        )

    evidence_tokens: dict[str, list[str]] = {}  # domain -> list of matching original field/file/purpose names
    domain_scores: dict[str, int] = {domain: 0 for domain in ALLOWED_BUSINESS_AREAS}

    # 1. Evaluate business purpose tokens (weighted 3x as primary signal)
    if business_purpose:
        bp_tokens = _tokenize_text(business_purpose)
        for domain, keywords in DOMAIN_TAXONOMY.items():
            matching_bp = [t for t in bp_tokens if t in keywords]
            if matching_bp:
                domain_scores[domain] += len(matching_bp) * 3
                evidence_tokens.setdefault(domain, []).extend(matching_bp[:5])

    # 2. Evaluate output evidence tokens (dataset names 2x, column headers 1x)
    for output in output_evidence:
        dataset_name = output.get("dataset", "")
        table_or_sheet = output.get("table_or_sheet", "")
        columns = output.get("columns", [])

        # Check dataset name tokens (weighted 2x)
        ds_tokens = _tokenize_text(dataset_name)
        if table_or_sheet:
            ds_tokens.extend(_tokenize_text(table_or_sheet))

        for domain, keywords in DOMAIN_TAXONOMY.items():
            matching_ds = [t for t in ds_tokens if t in keywords]
            if matching_ds:
                domain_scores[domain] += len(matching_ds) * 2
                evidence_tokens.setdefault(domain, []).append(dataset_name)

        # Check column header tokens
        for col in columns:
            col_tokens = _tokenize_text(col)
            for domain, keywords in DOMAIN_TAXONOMY.items():
                matching_col = [t for t in col_tokens if t in keywords]
                if matching_col:
                    domain_scores[domain] += len(matching_col)
                    evidence_tokens.setdefault(domain, []).append(col)

    # Sort domains by score descending
    ranked = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    top_domain, top_score = ranked[0]

    if top_score == 0:
        return BusinessAreaClassification(
            business_area="UNCLASSIFIED",
            confidence="UNCLASSIFIED",
            evidence=[],
            classification_source="deterministic_fallback",
            secondary_business_areas=[],
        )

    # Deduplicate matching evidence strings
    top_evidence = list(dict.fromkeys(evidence_tokens.get(top_domain, [])))[:10]

    # Secondary business areas with non-zero scores
    secondaries = [d for d, s in ranked[1:] if s > 0 and d != top_domain]

    # Confidence calculation
    if top_score >= 4 or (len(top_evidence) >= 3):
        conf = "HIGH"
    elif top_score >= 2:
        conf = "MEDIUM"
    else:
        conf = "LOW"

    return BusinessAreaClassification(
        business_area=top_domain,
        confidence=conf,
        evidence=top_evidence,
        classification_source="deterministic_fallback",
        secondary_business_areas=secondaries,
    )


def classify_workflow_business_area(
    result: CanonicalAnalysisResult,
    generator: LLMNarrativeGenerator | None = None,
    business_purpose: str | None = None,
    workflow_name: str | None = None,
) -> BusinessAreaClassification:
    """Classify workflow business area using LLM with deterministic validation and fallback."""
    output_evidence = extract_output_evidence_for_workflow(result)
    biz_purpose = ""
    if business_purpose is not None:
        biz_purpose = str(business_purpose)
    elif getattr(result, "business_summary", None) and isinstance(result.business_summary.business_purpose, str):
        biz_purpose = result.business_summary.business_purpose

    wf_name = "Workflow"
    if workflow_name:
        wf_name = str(workflow_name)
    elif getattr(result, "source", None) and getattr(result.source, "original_filename", None):
        wf_name = str(result.source.original_filename)
    elif getattr(result, "workflow", None) and getattr(result.workflow, "metadata", None) and getattr(result.workflow.metadata, "name", None):
        wf_name = str(result.workflow.metadata.name)

    # Workflows with no production outputs and no business purpose are UNCLASSIFIED
    if not output_evidence and not biz_purpose:
        return BusinessAreaClassification(
            business_area="UNCLASSIFIED",
            confidence="UNCLASSIFIED",
            evidence=[],
            classification_source="deterministic_fallback",
            secondary_business_areas=[],
        )

    deterministic_baseline = classify_business_area_deterministic(
        output_evidence, business_purpose=biz_purpose
    )

    # If no LLM generator provided, return deterministic baseline
    if generator is None:
        generator = get_default_generator()

    if not generator or not generator.client or not generator.client.is_available:
        return deterministic_baseline

    # Build allowed evidence strings
    allowed_evidence_strings: set[str] = set()
    for out in output_evidence:
        if out.get("dataset"):
            allowed_evidence_strings.add(out["dataset"])
        if out.get("table_or_sheet"):
            allowed_evidence_strings.add(out["table_or_sheet"])
        for col in out.get("columns", []):
            allowed_evidence_strings.add(col)
    if biz_purpose:
        for tok in _tokenize_text(biz_purpose):
            allowed_evidence_strings.add(tok)
        allowed_evidence_strings.add(biz_purpose)

    # Check LLM Cache
    cache_payload = {
        "evidence": output_evidence,
        "business_purpose": biz_purpose,
        "workflow_name": wf_name,
        "taxonomy_version": BUSINESS_AREA_CLASSIFICATION_PROMPT_VERSION,
    }
    cache_key = hashlib.sha256(
        f"business_area_classification:{json.dumps(cache_payload, sort_keys=True)}".encode("utf-8")
    ).hexdigest()

    cached = generator._cache.get(cache_key)
    if cached and cached.text:
        validated = _validate_llm_classification_response(cached.text, allowed_evidence_strings, biz_purpose)
        if validated:
            return validated

    # Generate LLM Narrative
    user_prompt = build_business_area_classification_user_prompt(
        output_evidence=output_evidence,
        business_purpose=biz_purpose,
        workflow_name=wf_name,
        descriptions=BUSINESS_AREA_DESCRIPTIONS,
    )

    try:
        raw_response = generator.client.generate(
            system_prompt=BUSINESS_AREA_CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=400,
        )

        validated = _validate_llm_classification_response(raw_response, allowed_evidence_strings, biz_purpose)
        if validated:
            generator._cache.set(
                cache_key,
                NarrativeResult(
                    text=raw_response,
                    source="llm",
                    model=generator.client.model_name,
                    prompt_version=BUSINESS_AREA_CLASSIFICATION_PROMPT_VERSION,
                ),
            )
            return validated
        else:
            logger.warning("[Business Area Classifier] LLM response failed deterministic validation. Falling back.")
            return deterministic_baseline

    except Exception as e:
        logger.warning("[Business Area Classifier] LLM invocation failed: %s. Using deterministic fallback.", e)
        return deterministic_baseline


def classify_portfolio_business_areas(
    results: list[CanonicalAnalysisResult],
    generator: LLMNarrativeGenerator | None = None,
) -> dict[str, BusinessAreaClassification]:
    """Classify a portfolio of workflows into enterprise business areas in a single coherent pass.

    Implements the 11-step pipeline:
    1. Obtain all workflows
    2. Obtain canonical business purpose for each workflow
    3. Obtain existing workflow classification evidence
    4. Obtain all business areas
    5. Ask LLM to classify workflows with structured output
    6. Validate LLM result against allowed business areas and expected workflow IDs
    7. Deterministically classify any invalid or missing workflows
    8. Return complete mapping of workflow_id -> BusinessAreaClassification
    """
    total_workflows = len(results)
    logger.info(
        "Business-area classification started: total_workflows=%d, total_business_areas=%d",
        total_workflows,
        len(ALLOWED_BUSINESS_AREAS),
    )

    if total_workflows == 0:
        return {}

    workflows_data: list[dict[str, Any]] = []
    deterministic_baselines: dict[str, BusinessAreaClassification] = {}
    allowed_evidence_by_wid: dict[str, set[str]] = {}
    purpose_by_wid: dict[str, str] = {}

    for res in results:
        wid = str(res.analysis_id) if hasattr(res, "analysis_id") else f"wf_{len(workflows_data)}"
        wname = "Workflow"
        if getattr(res, "source", None) and getattr(res.source, "original_filename", None):
            wname = str(res.source.original_filename)
        elif getattr(res, "workflow", None) and getattr(res.workflow, "metadata", None) and getattr(res.workflow.metadata, "name", None):
            wname = str(res.workflow.metadata.name)

        bpurpose = ""
        if getattr(res, "business_summary", None) and isinstance(res.business_summary.business_purpose, str):
            bpurpose = res.business_summary.business_purpose.strip()
        out_evidence = extract_output_evidence_for_workflow(res)

        det = classify_business_area_deterministic(out_evidence, business_purpose=bpurpose)
        deterministic_baselines[wid] = det
        purpose_by_wid[wid] = bpurpose

        allowed_strings: set[str] = set()
        for out in out_evidence:
            if out.get("dataset"):
                allowed_strings.add(out["dataset"])
            if out.get("table_or_sheet"):
                allowed_strings.add(out["table_or_sheet"])
            for col in out.get("columns", []):
                allowed_strings.add(col)
        if bpurpose:
            for tok in _tokenize_text(bpurpose):
                allowed_strings.add(tok)
            allowed_strings.add(bpurpose)
        allowed_evidence_by_wid[wid] = allowed_strings

        workflows_data.append({
            "workflow_id": wid,
            "workflow_name": wname,
            "business_purpose": bpurpose,
            "output_evidence": out_evidence,
        })

    # If LLM generator unavailable, immediately use deterministic baselines
    if generator is None:
        generator = get_default_generator()

    if not generator or not generator.client or not generator.client.is_available:
        logger.info(
            "LLM unavailable for business-area classification. Using deterministic fallback for all %d workflows.",
            total_workflows,
        )
        return deterministic_baselines

    # Check Cache
    cache_payload = {
        "workflows": [
            {
                "id": wf["workflow_id"],
                "name": wf["workflow_name"],
                "purpose": wf["business_purpose"],
                "evidence": wf["output_evidence"],
            }
            for wf in workflows_data
        ],
        "taxonomy_version": BUSINESS_AREA_CLASSIFICATION_PROMPT_VERSION,
    }
    cache_key = hashlib.sha256(
        f"portfolio_business_area_classification:{json.dumps(cache_payload, sort_keys=True)}".encode("utf-8")
    ).hexdigest()

    raw_response: str | None = None
    cached = generator._cache.get(cache_key)
    if cached and cached.text:
        raw_response = cached.text
    else:
        user_prompt = build_portfolio_business_area_classification_user_prompt(
            workflows_data,
            descriptions=BUSINESS_AREA_DESCRIPTIONS,
        )
        try:
            raw_response = generator.client.generate(
                system_prompt=PORTFOLIO_BUSINESS_AREA_CLASSIFICATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=2500,
            )
            generator._cache.set(
                cache_key,
                NarrativeResult(
                    text=raw_response,
                    source="llm",
                    model=generator.client.model_name,
                    prompt_version=BUSINESS_AREA_CLASSIFICATION_PROMPT_VERSION,
                ),
            )
        except Exception as e:
            logger.warning(
                "Portfolio LLM classification failed with exception: %s. Using deterministic fallback for all workflows.",
                e,
            )
            return deterministic_baselines

    # Validate structured response
    valid_llm_classifications, llm_returned_count = _validate_portfolio_llm_classification_response(
        raw_response=raw_response,
        expected_wids=set(deterministic_baselines.keys()),
        allowed_evidence_by_wid=allowed_evidence_by_wid,
        purpose_by_wid=purpose_by_wid,
    )

    final_classifications: dict[str, BusinessAreaClassification] = {}
    valid_llm_count = 0
    fallback_count = 0

    for wid, baseline in deterministic_baselines.items():
        if wid in valid_llm_classifications:
            final_classifications[wid] = valid_llm_classifications[wid]
            valid_llm_count += 1
        else:
            final_classifications[wid] = baseline
            fallback_count += 1

    logger.info(
        "Business-area classification completed: total_workflows=%d, total_business_areas=%d, "
        "llm_classifications_returned=%d, valid_llm_classifications=%d, fallback_classifications=%d, "
        "final_classified_workflows=%d",
        total_workflows,
        len(ALLOWED_BUSINESS_AREAS),
        llm_returned_count,
        valid_llm_count,
        fallback_count,
        len(final_classifications),
    )

    return final_classifications


def _validate_portfolio_llm_classification_response(
    raw_response: str,
    expected_wids: set[str],
    allowed_evidence_by_wid: dict[str, set[str]],
    purpose_by_wid: dict[str, str],
) -> tuple[dict[str, BusinessAreaClassification], int]:
    """Deterministically validate batch LLM classification response."""
    clean_text = raw_response.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
    except Exception as e:
        logger.warning("Failed to parse portfolio classification JSON: %s", e)
        return {}, 0

    items = []
    if isinstance(data, dict):
        items = data.get("workflow_classifications", [])
    elif isinstance(data, list):
        items = data

    if not isinstance(items, list):
        return {}, 0

    llm_returned_count = len(items)
    valid_map: dict[str, BusinessAreaClassification] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        wf_id = str(item.get("workflow_id", "")).strip()
        if not wf_id or wf_id not in expected_wids:
            logger.warning("Rejected unknown workflow ID from LLM response: '%s'", wf_id)
            continue

        area = item.get("business_area", "")
        if area not in ALLOWED_BUSINESS_AREAS and area != "UNCLASSIFIED":
            logger.warning("Rejected invalid business area from LLM for workflow '%s': '%s'", wf_id, area)
            continue

        conf = item.get("confidence", "MEDIUM")
        if conf not in ("HIGH", "MEDIUM", "LOW", "UNCLASSIFIED"):
            conf = "MEDIUM"

        raw_evidence = item.get("evidence", [])
        validated_ev: list[str] = []
        allowed_ev = allowed_evidence_by_wid.get(wf_id, set())
        b_purpose = purpose_by_wid.get(wf_id, "")

        if isinstance(raw_evidence, list):
            has_hallucination = False
            for ev in raw_evidence:
                ev_str = str(ev).strip()
                if not ev_str:
                    continue
                if ev_str in allowed_ev or (b_purpose and ev_str.lower() in b_purpose.lower()):
                    validated_ev.append(ev_str)
                else:
                    logger.warning("Rejected hallucinated evidence token '%s' for workflow '%s'", ev_str, wf_id)
                    has_hallucination = True
                    break
            if has_hallucination:
                continue

        secondaries = [
            str(sec)
            for sec in item.get("secondary_business_areas", [])
            if str(sec) in ALLOWED_BUSINESS_AREAS and str(sec) != area
        ]

        valid_map[wf_id] = BusinessAreaClassification(
            business_area=area,
            confidence=conf,
            evidence=validated_ev,
            classification_source="llm",
            secondary_business_areas=secondaries,
        )

    return valid_map, llm_returned_count


def _validate_llm_classification_response(
    raw_response: str,
    allowed_evidence: set[str],
    business_purpose: str = "",
) -> BusinessAreaClassification | None:
    """Deterministically validate the LLM classification response."""
    clean_text = raw_response.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        data = json.loads(clean_text)
    except Exception as e:
        logger.warning("Failed to parse classification JSON: %s", e)
        return None

    if not isinstance(data, dict):
        return None

    area = data.get("business_area", "")
    if area not in ALLOWED_BUSINESS_AREAS and area != "UNCLASSIFIED":
        logger.warning("Rejected unsupported business area: '%s'", area)
        return None

    conf = data.get("confidence", "MEDIUM")
    if conf not in ("HIGH", "MEDIUM", "LOW", "UNCLASSIFIED"):
        conf = "MEDIUM"

    raw_evidence = data.get("evidence", [])
    if not isinstance(raw_evidence, list):
        return None

    validated_evidence: list[str] = []
    for ev in raw_evidence:
        ev_str = str(ev).strip()
        if not ev_str:
            continue
        if ev_str in allowed_evidence or (business_purpose and ev_str.lower() in business_purpose.lower()):
            validated_evidence.append(ev_str)
        else:
            logger.warning("Rejected hallucinated evidence token '%s'.", ev_str)
            return None

    secondaries = [
        str(sec)
        for sec in data.get("secondary_business_areas", [])
        if str(sec) in ALLOWED_BUSINESS_AREAS and str(sec) != area
    ]

    return BusinessAreaClassification(
        business_area=area,
        confidence=conf,
        evidence=validated_evidence,
        classification_source="llm",
        secondary_business_areas=secondaries,
    )

