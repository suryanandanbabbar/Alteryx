"""Purely Deterministic Workflow Criticality Engine.

Evaluates workflow criticality based on exactly 5 factors across Technical (60%) and Operational (40%) categories:

Criticality
• Technical Factors
  • Number of downstream outputs
  • Number of upstream sources
  • Number of ETL workflows consuming the output of this workflow
• Operational Factors
  • Last Run
  • Frequency
* Business impact factors can be added further once the information about downstream targets/consumers is available

CRITICAL INVARIANTS:
1. Zero LLM involvement. 100% deterministic, reproducible, and auditable.
2. Exactly 5 factors, each weighted 20% (0.20).
3. Technical subtotal = 60%, Operational subtotal = 40%, Total = 100%.
4. Score bounded to [0.0, 100.0].
   - 0–34: LOW
   - 35–69: MEDIUM
   - 70–100: HIGH
5. Missing/unknown evidence is never fabricated (normalized explicitly to 0.0 with clear evidence label).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Central Configuration & Calibration Thresholds
# ---------------------------------------------------------------------------

CRITICALITY_FACTOR_WEIGHT: float = 0.20  # 20% per factor
TECHNICAL_WEIGHT_TOTAL: float = 0.60    # 60%
OPERATIONAL_WEIGHT_TOTAL: float = 0.40  # 40%

CRITICALITY_LOW_MAX: float = 34.0
CRITICALITY_MEDIUM_MAX: float = 69.0

BUSINESS_IMPACT_NOTE: str = (
    "* Business impact factors can be added further once the information about downstream targets/consumers is available"
)


@dataclass
class CriticalityAssessment:
    """Criticality assessment result containing deterministic 5-factor metrics and breakdown."""
    score: float
    level: Literal["HIGH", "MEDIUM", "LOW"]
    technical_score: float = 0.0
    operational_score: float = 0.0
    factors: list[str] = field(default_factory=list)
    breakdown: dict[str, float] = field(default_factory=dict)
    factor_breakdown: dict[str, Any] = field(default_factory=dict)
    criticality_justification: str = ""
    business_consequence: str = ""
    dependency_impact: str = ""
    affected_scope: str = ""
    migration_implication: str = ""
    confidence: str = "HIGH"
    justification_source: str = "deterministic"
    criticality_source: str = "deterministic"
    source: str = "deterministic"
    business_impact_note: str = BUSINESS_IMPACT_NOTE
    factor_assessments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "criticality_score": self.score,
            "level": self.level,
            "criticality_level": self.level,
            "technical_score": self.technical_score,
            "operational_score": self.operational_score,
            "factors": self.factors,
            "criticality_factors": self.factors,
            "breakdown": self.breakdown,
            "factor_breakdown": self.factor_breakdown,
            "criticality_justification": self.criticality_justification,
            "business_consequence": self.business_consequence,
            "dependency_impact": self.dependency_impact,
            "affected_scope": self.affected_scope,
            "migration_implication": self.migration_implication,
            "confidence": self.confidence,
            "justification_source": self.justification_source,
            "criticality_source": self.criticality_source,
            "source": self.source,
            "business_impact_note": self.business_impact_note,
            "factor_assessments": self.factor_assessments,
        }


@dataclass
class PortfolioDependencyContext:
    """Deterministic cross-workflow dependency context derived from the portfolio."""
    # Mapping of target dataset name -> list of (workflow_id, filename) producing it
    target_to_producers: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # Mapping of source dataset name -> list of (workflow_id, filename) consuming it
    source_to_consumers: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # Set of shared target datasets (produced by multiple workflows or consumed cross-workflow)
    shared_targets: set[str] = field(default_factory=set)
    # Set of shared source datasets (consumed by multiple workflows)
    shared_sources: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Factor Normalization Functions (0.0 to 100.0)
# ---------------------------------------------------------------------------

def normalize_downstream_outputs_score(targets: list[str]) -> tuple[float, str]:
    """Factor 1: Number of downstream outputs (Technical, 20% weight)."""
    count = len(targets)
    if count == 0:
        return 0.0, "0 downstream outputs"
    elif count == 1:
        return 40.0, "1 downstream output"
    elif count == 2:
        return 70.0, "2 downstream outputs"
    elif count == 3:
        return 85.0, "3 downstream outputs"
    else:
        score = min(100.0, 85.0 + (count - 3) * 5.0)
        return score, f"{count} downstream outputs"


def normalize_upstream_sources_score(sources: list[str]) -> tuple[float, str]:
    """Factor 2: Number of upstream sources (Technical, 20% weight)."""
    count = len(sources)
    if count == 0:
        return 0.0, "0 upstream sources"
    elif count == 1:
        return 40.0, "1 upstream source"
    elif count == 2:
        return 70.0, "2 upstream sources"
    elif count == 3:
        return 85.0, "3 upstream sources"
    else:
        score = min(100.0, 85.0 + (count - 3) * 5.0)
        return score, f"{count} upstream sources"


def normalize_etl_consumers_score(downstream_consumers: list[str]) -> tuple[float, str]:
    """Factor 3: Number of ETL workflows consuming the output of this workflow (Technical, 20% weight)."""
    count = len(downstream_consumers)
    if count == 0:
        return 0.0, "0 consuming ETL workflows"
    elif count == 1:
        return 60.0, "1 consuming ETL workflow"
    elif count == 2:
        return 80.0, "2 consuming ETL workflows"
    elif count == 3:
        return 90.0, "3 consuming ETL workflows"
    else:
        score = min(100.0, 90.0 + (count - 3) * 5.0)
        return score, f"{count} consuming ETL workflows"


def normalize_last_run_score(last_run: Any) -> tuple[float, str]:
    """Factor 4: Last Run (Operational, 20% weight)."""
    if last_run is None:
        return 0.0, "Not documented"
    if isinstance(last_run, (int, float)):
        days = float(last_run)
        if days <= 7:
            return 100.0, f"{days:.0f} days ago"
        elif days <= 30:
            return 80.0, f"{days:.0f} days ago"
        elif days <= 90:
            return 60.0, f"{days:.0f} days ago"
        elif days <= 180:
            return 40.0, f"{days:.0f} days ago"
        elif days <= 365:
            return 20.0, f"{days:.0f} days ago"
        else:
            return 10.0, f"{days:.0f} days ago"

    s = str(last_run).strip()
    if not s or s.lower() in ("not documented", "unknown", "none", "n/a", "null"):
        return 0.0, "Not documented"

    s_low = s.lower()
    if any(w in s_low for w in ("today", "yesterday", "recent", "now", "hour", "minute", "sec")):
        return 100.0, s

    m_day = re.search(r"(\d+)\s*day", s_low)
    if m_day:
        d = int(m_day.group(1))
        if d <= 7:
            return 100.0, s
        elif d <= 30:
            return 80.0, s
        elif d <= 90:
            return 60.0, s
        elif d <= 180:
            return 40.0, s
        elif d <= 365:
            return 20.0, s
        else:
            return 10.0, s

    m_wk = re.search(r"(\d+)\s*week", s_low)
    if m_wk:
        w = int(m_wk.group(1))
        if w <= 1:
            return 100.0, s
        elif w <= 4:
            return 80.0, s
        elif w <= 12:
            return 60.0, s
        elif w <= 26:
            return 40.0, s
        elif w <= 52:
            return 20.0, s
        else:
            return 10.0, s

    m_mo = re.search(r"(\d+)\s*month", s_low)
    if m_mo:
        mo = int(m_mo.group(1))
        if mo <= 1:
            return 80.0, s
        elif mo <= 3:
            return 60.0, s
        elif mo <= 6:
            return 40.0, s
        elif mo <= 12:
            return 20.0, s
        else:
            return 10.0, s

    m_yr = re.search(r"(\d+)\s*year", s_low)
    if m_yr:
        y = int(m_yr.group(1))
        if y <= 1:
            return 20.0, s
        else:
            return 10.0, s

    if any(w in s_low for w in ("recent", "daily", "active")):
        return 100.0, s
    elif any(w in s_low for w in ("monthly", "last month")):
        return 80.0, s
    elif any(w in s_low for w in ("quarterly", "3 months")):
        return 60.0, s
    elif any(w in s_low for w in ("old", "stale", "dormant", "deprecated", "inactive")):
        return 10.0, s
    else:
        return 40.0, s


def normalize_frequency_score(frequency: Any) -> tuple[float, str]:
    """Factor 5: Frequency (Operational, 20% weight)."""
    if frequency is None:
        return 0.0, "Not documented"
    s = str(frequency).strip()
    if not s or s.lower() in ("not documented", "unknown", "none", "n/a", "null"):
        return 0.0, "Not documented"

    s_low = s.lower()
    if any(w in s_low for w in ("realtime", "real-time", "streaming", "continuous", "hourly", "every hour")):
        return 100.0, s
    elif any(w in s_low for w in ("daily", "business daily", "weekdays", "every day", "nightly", "every 24 hours")):
        return 90.0, s
    elif any(w in s_low for w in ("weekly", "bi-weekly", "biweekly", "every week", "every 2 weeks", "fortnightly")):
        return 75.0, s
    elif any(w in s_low for w in ("monthly", "every month", "every 4 weeks", "end of month", "eom")):
        return 60.0, s
    elif any(w in s_low for w in ("quarterly", "every quarter", "every 3 months", "end of quarter", "eoq")):
        return 45.0, s
    elif any(w in s_low for w in ("semi-annually", "biannually", "bi-annually", "every 6 months", "half-yearly")):
        return 30.0, s
    elif any(w in s_low for w in ("annually", "yearly", "every year", "end of year", "eoy")):
        return 20.0, s
    elif any(w in s_low for w in ("ad-hoc", "adhoc", "on-demand", "manual", "as needed", "triggered")):
        return 15.0, s
    else:
        return 25.0, s


# ---------------------------------------------------------------------------
# Main Deterministic 5-Factor Criticality Calculation
# ---------------------------------------------------------------------------

def calculate_workflow_criticality(
    workflow_id: str,
    workflow_filename: str,
    sources: list[str],
    targets: list[str],
    inspection_sinks: list[str] | None = None,
    context: PortfolioDependencyContext | None = None,
    operational_metadata: dict[str, Any] | None = None,
    business_purpose: str = "",
    business_function: str = "",
) -> CriticalityAssessment:
    """Deterministically compute workflow criticality using the 5-factor model (Technical 60%, Operational 40%)."""
    ctx = context or PortfolioDependencyContext()
    inspection_sinks = inspection_sinks or []

    # 1. Technical Factor 1: Number of downstream outputs (20%)
    out_score, out_raw = normalize_downstream_outputs_score(targets)

    # 2. Technical Factor 2: Number of upstream sources (20%)
    src_score, src_raw = normalize_upstream_sources_score(sources)

    # 3. Technical Factor 3: Number of ETL workflows consuming the output of this workflow (20%)
    downstream_consumers: list[str] = []
    for t in targets:
        for c_wid, c_fname in ctx.source_to_consumers.get(t, []):
            if c_wid != workflow_id and c_fname not in downstream_consumers:
                downstream_consumers.append(c_fname)
    etl_score, etl_raw = normalize_etl_consumers_score(downstream_consumers)

    # 4. Operational Factor 4: Last Run (20%)
    last_run_input = None
    frequency_input = None
    if operational_metadata and isinstance(operational_metadata, dict):
        op_dict = dict(operational_metadata)
        if isinstance(operational_metadata.get("MetaInfo"), dict):
            op_dict.update(operational_metadata["MetaInfo"])

        norm_map = {k.lower().replace("_", "").replace(" ", ""): v for k, v in op_dict.items() if isinstance(k, str)}

        last_run_input = (
            op_dict.get("last_run")
            or op_dict.get("last_executed")
            or op_dict.get("last_run_date")
            or op_dict.get("lastRun")
            or op_dict.get("LastRun")
            or norm_map.get("lastrun")
            or norm_map.get("lastexecuted")
            or norm_map.get("lastrundate")
            or norm_map.get("rundate")
        )
        frequency_input = (
            op_dict.get("frequency")
            or op_dict.get("schedule")
            or op_dict.get("run_frequency")
            or op_dict.get("frequency_schedule")
            or op_dict.get("Frequency")
            or norm_map.get("frequency")
            or norm_map.get("schedule")
            or norm_map.get("runfrequency")
            or norm_map.get("frequencyschedule")
        )
    last_run_score, last_run_raw = normalize_last_run_score(last_run_input)

    # 5. Operational Factor 5: Frequency (20%)
    freq_score, freq_raw = normalize_frequency_score(frequency_input)

    # Subtotals & Total Calculation
    technical_score = round((out_score + src_score + etl_score) * CRITICALITY_FACTOR_WEIGHT, 1)
    operational_score = round((last_run_score + freq_score) * CRITICALITY_FACTOR_WEIGHT, 1)
    final_score = round(max(0.0, min(100.0, technical_score + operational_score)), 1)

    if final_score >= CRITICALITY_MEDIUM_MAX + 1:
        level: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    elif final_score >= CRITICALITY_LOW_MAX + 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    out_count = len(targets)
    src_count = len(sources)
    etl_count = len(downstream_consumers)

    factor_breakdown: dict[str, Any] = {
        "downstream_outputs": {
            "name": "Downstream outputs",
            "category": "Technical",
            "raw_value": out_count,
            "display_value": out_raw,
            "raw_evidence": out_raw,
            "evidence_display": out_raw,
            "weight_pct": 20.0,
            "factor_score": out_score,
            "weighted_contribution_pct": round(out_score * CRITICALITY_FACTOR_WEIGHT, 1),
            "evidence_details": list(targets),
        },
        "upstream_sources": {
            "name": "Upstream sources",
            "category": "Technical",
            "raw_value": src_count,
            "display_value": src_raw,
            "raw_evidence": src_raw,
            "evidence_display": src_raw,
            "weight_pct": 20.0,
            "factor_score": src_score,
            "weighted_contribution_pct": round(src_score * CRITICALITY_FACTOR_WEIGHT, 1),
            "evidence_details": list(sources),
        },
        "etl_consumers": {
            "name": "ETL workflow consumers",
            "category": "Technical",
            "raw_value": etl_count,
            "display_value": etl_raw,
            "raw_evidence": etl_raw,
            "evidence_display": etl_raw,
            "weight_pct": 20.0,
            "factor_score": etl_score,
            "weighted_contribution_pct": round(etl_score * CRITICALITY_FACTOR_WEIGHT, 1),
            "evidence_details": list(downstream_consumers),
        },
        "last_run": {
            "name": "Last Run",
            "category": "Operational",
            "raw_value": last_run_raw,
            "display_value": last_run_raw,
            "raw_evidence": last_run_raw,
            "evidence_display": last_run_raw,
            "weight_pct": 20.0,
            "factor_score": last_run_score,
            "weighted_contribution_pct": round(last_run_score * CRITICALITY_FACTOR_WEIGHT, 1),
            "evidence_details": [last_run_raw] if last_run_raw != "Not documented" else [],
        },
        "frequency": {
            "name": "Frequency",
            "category": "Operational",
            "raw_value": freq_raw,
            "display_value": freq_raw,
            "raw_evidence": freq_raw,
            "evidence_display": freq_raw,
            "weight_pct": 20.0,
            "factor_score": freq_score,
            "weighted_contribution_pct": round(freq_score * CRITICALITY_FACTOR_WEIGHT, 1),
            "evidence_details": [freq_raw] if freq_raw != "Not documented" else [],
        },
    }

    factors = [
        f"Downstream outputs -> Value: {out_count} | Weight: 20% -> Factor Score: {out_score:.1f}/100 | Contribution: {out_score * CRITICALITY_FACTOR_WEIGHT:.1f}%",
        f"Upstream sources -> Value: {src_count} | Weight: 20% -> Factor Score: {src_score:.1f}/100 | Contribution: {src_score * CRITICALITY_FACTOR_WEIGHT:.1f}%",
        f"ETL workflow consumers -> Value: {etl_count} | Weight: 20% -> Factor Score: {etl_score:.1f}/100 | Contribution: {etl_score * CRITICALITY_FACTOR_WEIGHT:.1f}%",
        f"Last Run -> Value: {last_run_raw} | Weight: 20% -> Factor Score: {last_run_score:.1f}/100 | Contribution: {last_run_score * CRITICALITY_FACTOR_WEIGHT:.1f}%",
        f"Frequency -> Value: {freq_raw} | Weight: 20% -> Factor Score: {freq_score:.1f}/100 | Contribution: {freq_score * CRITICALITY_FACTOR_WEIGHT:.1f}%",
    ]

    justification = (
        f"Deterministic 5-factor evaluation (Technical: {technical_score:.1f}/60%, Operational: {operational_score:.1f}/40%). "
        f"Outputs: {out_raw}; Sources: {src_raw}; Consuming Workflows: {etl_raw}; "
        f"Last Run: {last_run_raw}; Frequency: {freq_raw}."
    )

    return CriticalityAssessment(
        score=final_score,
        level=level,
        technical_score=technical_score,
        operational_score=operational_score,
        factors=factors,
        breakdown={
            "downstream_outputs": out_score,
            "upstream_sources": src_score,
            "etl_consumers": etl_score,
            "last_run": last_run_score,
            "frequency": freq_score,
            "technical_subtotal": technical_score,
            "operational_subtotal": operational_score,
        },
        factor_breakdown=factor_breakdown,
        criticality_justification=justification,
        business_consequence=f"Failure interrupts {len(targets)} downstream output(s) and {len(downstream_consumers)} consuming ETL workflow(s).",
        dependency_impact=f"{len(downstream_consumers)} downstream consuming ETL workflow(s) directly depend on this workflow's outputs.",
        affected_scope=f"Consumes {len(sources)} source(s) and publishes {len(targets)} deliverable(s).",
        migration_implication=f"Migration priority based on {level} criticality ({final_score:.1f}/100). Validate interface dependencies.",
        confidence="HIGH",
        justification_source="deterministic",
        criticality_source="deterministic",
        source="deterministic",
        business_impact_note=BUSINESS_IMPACT_NOTE,
        factor_assessments=factor_breakdown,
    )


def build_criticality_evidence_package(
    workflow_id: str,
    workflow_filename: str,
    sources: list[str],
    targets: list[str],
    inspection_sinks: list[str],
    context: PortfolioDependencyContext | None = None,
    operational_metadata: dict[str, Any] | None = None,
    business_purpose: str = "",
    business_function: str = "",
    business_area: str = "",
    deterministic_counts: dict[str, int] | None = None,
) -> Any:
    """Construct a deterministic evidence package."""
    from awa.llm.schemas import CriticalityEvidencePackage

    ctx = context or PortfolioDependencyContext()
    downstream_consumers: list[str] = []
    for t in targets:
        for c_wid, c_fname in ctx.source_to_consumers.get(t, []):
            if c_wid != workflow_id and c_fname not in downstream_consumers:
                downstream_consumers.append(c_fname)

    upstream_producers: list[str] = []
    for s in sources:
        for p_wid, p_fname in ctx.target_to_producers.get(s, []):
            if p_wid != workflow_id and p_fname not in upstream_producers:
                upstream_producers.append(p_fname)

    det_crit = calculate_workflow_criticality(
        workflow_id=workflow_id,
        workflow_filename=workflow_filename,
        sources=sources,
        targets=targets,
        inspection_sinks=inspection_sinks,
        context=ctx,
        operational_metadata=operational_metadata,
        business_purpose=business_purpose,
        business_function=business_function,
    )

    counts = dict(deterministic_counts or {})
    counts.setdefault("source_count", len(sources))
    counts.setdefault("target_count", len(targets))
    counts.setdefault("inspection_sink_count", len(inspection_sinks))
    counts.setdefault("downstream_consumer_count", len(downstream_consumers))
    counts.setdefault("upstream_producer_count", len(upstream_producers))

    return CriticalityEvidencePackage(
        workflow_id=workflow_id,
        workflow_filename=workflow_filename,
        business_purpose=business_purpose,
        business_function=business_function,
        business_area=business_area,
        production_targets=targets,
        inspection_sinks=inspection_sinks,
        upstream_producers=upstream_producers,
        downstream_consumers=downstream_consumers,
        shared_targets=[t for t in targets if t in ctx.shared_targets],
        shared_sources=[s for s in sources if s in ctx.shared_sources],
        dependency_position="Isolated Process" if not downstream_consumers and not upstream_producers else ("Midstream Integration Hub" if downstream_consumers and upstream_producers else ("Upstream Root Producer" if downstream_consumers else "Leaf Consumer")),
        deterministic_counts=counts,
        semantic_impact_signals=[],
        operational_metadata=operational_metadata or {},
        deterministic_reference_score=det_crit.score,
        deterministic_reference_level=det_crit.level,
    )
