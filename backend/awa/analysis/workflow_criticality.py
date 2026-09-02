"""Deterministic Workflow Criticality Engine.

Evaluates workflow criticality based on impact and dependency signals:
1. Downstream Workflow Dependencies (27.8% normalized)
2. Production Deliverables (22.2% normalized)
3. Output Consumers / Shared Deliverables (22.2% normalized)
4. Dependency Position in Portfolio Pipeline (16.7% normalized)
5. Shared Sources Ecosystem Participation (11.1% normalized)
6. Optional Operational Metadata (10% when available; redistributed when absent)

CRITICAL INVARIANTS:
1. Criticality != Complexity. Criticality measures blast radius / business impact if stopped.
2. Zero LLM involvement. Purely deterministic and auditable.
3. Production targets strictly distinguished from Browse/BrowseV2 inspection sinks.
4. Operational metadata is never fabricated. Missing metadata triggers explicit proportional weight redistribution.
5. Clamped normalized score between 0.0 and 100.0.
   - 0–34: LOW
   - 35–69: MEDIUM
   - 70–100: HIGH
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

# ---------------------------------------------------------------------------
# Semantic Impact Patterns for Business Purpose Assessment
# ---------------------------------------------------------------------------

DELIVERABLE_PATTERN = re.compile(
    r"\b(generates?|produces?|publishes?|creates?|outputs?|builds?|maintains?|distributes?)\b.*"
    r"\b(statutory|regulatory|compliance|board|financial|executive|master\s+data|reconciliation|deliverables?|official|filing|ledger|audit)\b",
    re.IGNORECASE,
)

SCOPE_PATTERN = re.compile(
    r"\b(enterprise-wide|organization-wide|company-wide|portfolio-wide|nationwide|global|across\s+all\s+(lines|policies|claims|regions|products|branches)|multi-regional?|entire\s+(portfolio|estate|organization))\b",
    re.IGNORECASE,
)

CUSTOMER_PATTERN = re.compile(
    r"\b(calculates?|determines?|processes?|adjudicates?|manages?|supports?)\b.*"
    r"\b(claimant|policyholder|insured|customer)\b.*"
    r"\b(benefits?|payments?|indemnity|settlement|coverage|premiums?|eligibility|billing|claims?)\b",
    re.IGNORECASE,
)

CLIENT_PATTERN = re.compile(
    r"\b(prepares?|distributes?|publishes?|calculates?|delivers?)\b.*"
    r"\b(client|broker|agent|producer|distributor|counterparty)\b.*"
    r"\b(statements?|commissions?|reports?|remittances?|commitments?|invoices?)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Central Configuration
# ---------------------------------------------------------------------------

BASE_CRITICALITY_WEIGHTS: dict[str, float] = {
    "downstream_dependency": 0.25,
    "production_outputs": 0.20,
    "output_consumers": 0.20,
    "dependency_position": 0.15,
    "shared_sources": 0.10,
    "operational": 0.10,
}

CRITICALITY_LOW_MAX: float = 34.0
CRITICALITY_MEDIUM_MAX: float = 69.0


@dataclass
class CriticalityAssessment:
    """Criticality assessment result containing deterministic metrics and business justification."""
    score: float
    level: Literal["HIGH", "MEDIUM", "LOW"]
    factors: list[str] = field(default_factory=list)
    breakdown: dict[str, float] = field(default_factory=dict)
    criticality_justification: str = ""
    business_consequence: str = ""
    dependency_impact: str = ""
    affected_scope: str = ""
    migration_implication: str = ""
    confidence: str = "HIGH"
    justification_source: str = "deterministic_fallback"
    factor_assessments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "factors": self.factors,
            "breakdown": self.breakdown,
            "criticality_justification": self.criticality_justification,
            "business_consequence": self.business_consequence,
            "dependency_impact": self.dependency_impact,
            "affected_scope": self.affected_scope,
            "migration_implication": self.migration_implication,
            "confidence": self.confidence,
            "justification_source": self.justification_source,
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


def calculate_workflow_criticality(
    workflow_id: str,
    workflow_filename: str,
    sources: list[str],
    targets: list[str],
    inspection_sinks: list[str],
    context: PortfolioDependencyContext | None = None,
    operational_metadata: dict[str, Any] | None = None,
    business_purpose: str = "",
    business_function: str = "",
) -> CriticalityAssessment:
    """Deterministically compute workflow criticality."""
    ctx = context or PortfolioDependencyContext()
    factors: list[str] = []

    # -----------------------------------------------------------------------
    # 1. Production Deliverables (Strictly excluding inspection sinks)
    # -----------------------------------------------------------------------
    prod_targets_count = len(targets)
    if prod_targets_count == 0:
        prod_score = 0.0
        if inspection_sinks:
            factors.append("No production deliverables (inspection sinks only)")
        else:
            factors.append("Zero output deliverables configured")
    elif prod_targets_count == 1:
        prod_score = 45.0
        factors.append(f"1 production deliverable ({targets[0]})")
    elif prod_targets_count == 2:
        prod_score = 70.0
        factors.append("2 production deliverables configured")
    elif prod_targets_count == 3:
        prod_score = 85.0
        factors.append("3 production deliverables configured")
    else:
        prod_score = min(100.0, 85.0 + (prod_targets_count - 3) * 5.0)
        factors.append(f"{prod_targets_count} production deliverables configured")

    # -----------------------------------------------------------------------
    # 2. Downstream Workflow Dependencies
    # (Workflows in portfolio that consume this workflow's production outputs)
    # -----------------------------------------------------------------------
    downstream_consumers: dict[str, str] = {}  # wf_id -> filename
    shared_outputs_produced: list[str] = []

    for t in targets:
        # Check consumers of target t
        consumers = ctx.source_to_consumers.get(t, [])
        for c_wid, c_fname in consumers:
            if c_wid != workflow_id:
                downstream_consumers[c_wid] = c_fname

        # Check if t is an enterprise shared target
        if t in ctx.shared_targets:
            shared_outputs_produced.append(t)

    downstream_count = len(downstream_consumers)
    if downstream_count == 0:
        downstream_score = 0.0
    elif downstream_count == 1:
        downstream_score = 55.0
        consumer_name = list(downstream_consumers.values())[0]
        factors.append(f"1 downstream consumer ({consumer_name})")
    elif downstream_count == 2:
        downstream_score = 80.0
        factors.append(f"2 downstream workflow consumers")
    else:
        downstream_score = min(100.0, 80.0 + downstream_count * 6.0)
        factors.append(f"{downstream_count} downstream workflow consumers")

    # -----------------------------------------------------------------------
    # 3. Output Consumers & Shared Deliverables
    # -----------------------------------------------------------------------
    if shared_outputs_produced:
        shared_count = len(shared_outputs_produced)
        consumers_score = min(100.0, shared_count * 50.0 + downstream_count * 15.0)
        factors.append(f"{shared_count} shared enterprise deliverable{'s' if shared_count > 1 else ''}")
    elif downstream_count > 0:
        consumers_score = min(75.0, downstream_count * 25.0)
    else:
        consumers_score = 0.0

    # -----------------------------------------------------------------------
    # 4. Dependency Position in Portfolio Pipeline
    # -----------------------------------------------------------------------
    # Check if this workflow consumes outputs produced by another workflow
    upstream_producers: dict[str, str] = {}
    for s in sources:
        producers = ctx.target_to_producers.get(s, [])
        for p_wid, p_fname in producers:
            if p_wid != workflow_id:
                upstream_producers[p_wid] = p_fname

    upstream_count = len(upstream_producers)

    if downstream_count > 0 and upstream_count == 0:
        # Upstream Root Producer: Feeds downstream workflows without dependencies
        position_score = 85.0
        factors.append("Upstream root producer for portfolio workflows")
    elif downstream_count > 0 and upstream_count > 0:
        # Midstream Integration Hub: Consumes and produces downstream dependencies
        position_score = 95.0
        factors.append("Critical midstream pipeline hub")
    elif downstream_count == 0 and upstream_count > 0:
        # Leaf Consumer: Downstream consumer of other workflows
        position_score = 40.0
        factors.append("Downstream consumer of portfolio workflows")
    else:
        position_score = 15.0

    # -----------------------------------------------------------------------
    # 5. Shared Upstream Ingestion
    # -----------------------------------------------------------------------
    shared_sources_consumed = [s for s in sources if s in ctx.shared_sources]
    if len(shared_sources_consumed) >= 3:
        sources_score = 80.0
        factors.append(f"Consumes {len(shared_sources_consumed)} shared portfolio inputs")
    elif len(shared_sources_consumed) >= 1:
        sources_score = 50.0
        factors.append(f"Consumes {len(shared_sources_consumed)} shared portfolio input(s)")
    else:
        sources_score = 0.0

    # -----------------------------------------------------------------------
    # 6. Operational Impact Assessment & Calibrated Score
    # (Business Deliverables, Scope, Customers, Clients)
    # -----------------------------------------------------------------------
    op_score = 0.0
    has_operational = False
    purpose_factors: list[str] = []

    if operational_metadata and isinstance(operational_metadata, dict):
        op_score = float(operational_metadata.get("score", 50.0))
        has_operational = True
        factors.append("Operational metadata included")
    else:
        # Evaluate semantic business impact from business_function and business_purpose
        combined_text = f"{business_function} {business_purpose}".strip()
        if combined_text:
            matched_dimensions = 0
            # 1. Business Deliverables Impact: mandatory/official reporting, filings, ledgers (+25.0)
            if DELIVERABLE_PATTERN.search(combined_text):
                matched_dimensions += 1
                purpose_factors.append("Business impact: critical reporting/deliverable")

            # 2. Business Scope Impact: enterprise-wide, portfolio-wide, national operational breadth (+25.0)
            if SCOPE_PATTERN.search(combined_text):
                matched_dimensions += 1
                purpose_factors.append("Business impact: enterprise operational scope")

            # 3. Customer Impact: claimant, policyholder, insured, customer benefits/coverage (+25.0)
            if CUSTOMER_PATTERN.search(combined_text):
                matched_dimensions += 1
                purpose_factors.append("Business impact: direct customer/claimant impact")

            # 4. Client Impact: external broker, client, partner statements/commissions (+25.0)
            if CLIENT_PATTERN.search(combined_text):
                matched_dimensions += 1
                purpose_factors.append("Business impact: client/partner deliverable")

            if matched_dimensions > 0:
                op_score = min(100.0, float(matched_dimensions * 25.0))
                has_operational = True

    factors.extend(purpose_factors)

    if has_operational:
        weights = dict(BASE_CRITICALITY_WEIGHTS)
    else:
        # Explicit redistribution policy: Redistribute 0.10 weight proportionally across 5 active factors
        active_sum = sum(w for k, w in BASE_CRITICALITY_WEIGHTS.items() if k != "operational")  # 0.90
        weights = {k: BASE_CRITICALITY_WEIGHTS[k] / active_sum for k in BASE_CRITICALITY_WEIGHTS if k != "operational"}
        op_score = 0.0

    final_score = (
        weights["downstream_dependency"] * downstream_score
        + weights["production_outputs"] * prod_score
        + weights["output_consumers"] * consumers_score
        + weights["dependency_position"] * position_score
        + weights["shared_sources"] * sources_score
    )
    if has_operational:
        final_score += weights["operational"] * op_score

    final_score = round(max(0.0, min(100.0, final_score)), 1)

    if final_score >= CRITICALITY_MEDIUM_MAX + 1:
        level: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    elif final_score >= CRITICALITY_LOW_MAX + 1:
        level = "MEDIUM"
    else:
        level = "LOW"

    return CriticalityAssessment(
        score=final_score,
        level=level,
        factors=factors[:6],
        breakdown={
            "downstream_dependency": downstream_score,
            "production_outputs": prod_score,
            "output_consumers": consumers_score,
            "dependency_position": position_score,
            "shared_sources": sources_score,
            "operational": op_score,
            "business_purpose_impact": op_score,
        },
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
    """Construct a compact deterministic evidence package for LLM criticality evaluation."""
    from awa.llm.schemas import CriticalityEvidencePackage

    ctx = context or PortfolioDependencyContext()

    # Determine downstream consumers and shared targets
    downstream_consumers: dict[str, str] = {}
    shared_outputs_produced: list[str] = []
    for t in targets:
        consumers = ctx.source_to_consumers.get(t, [])
        for c_wid, c_fname in consumers:
            if c_wid != workflow_id:
                downstream_consumers[c_wid] = c_fname
        if t in ctx.shared_targets:
            shared_outputs_produced.append(t)

    # Determine upstream producers
    upstream_producers: dict[str, str] = {}
    for s in sources:
        producers = ctx.target_to_producers.get(s, [])
        for p_wid, p_fname in producers:
            if p_wid != workflow_id:
                upstream_producers[p_wid] = p_fname

    downstream_count = len(downstream_consumers)
    upstream_count = len(upstream_producers)

    # Determine dependency position
    if downstream_count > 0 and upstream_count == 0:
        position = "Upstream Root Producer"
    elif downstream_count > 0 and upstream_count > 0:
        position = "Midstream Integration Hub"
    elif downstream_count == 0 and upstream_count > 0:
        position = "Leaf Consumer"
    else:
        position = "Isolated Process"

    shared_sources_consumed = [s for s in sources if s in ctx.shared_sources]

    # Semantic business impact signals
    semantic_signals: list[str] = []
    combined_text = f"{business_function} {business_purpose}".strip()
    if combined_text:
        if DELIVERABLE_PATTERN.search(combined_text):
            semantic_signals.append("Statutory / compliance / financial reporting deliverable")
        if SCOPE_PATTERN.search(combined_text):
            semantic_signals.append("Enterprise-wide operational breadth")
        if CUSTOMER_PATTERN.search(combined_text):
            semantic_signals.append("Customer / claimant / policyholder benefit or coverage impact")
        if CLIENT_PATTERN.search(combined_text):
            semantic_signals.append("External client / broker / agent deliverable or commission")

    # Calculate deterministic baseline for audit/reference
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
    counts.setdefault("downstream_consumer_count", downstream_count)
    counts.setdefault("upstream_producer_count", upstream_count)

    return CriticalityEvidencePackage(
        workflow_id=workflow_id,
        workflow_filename=workflow_filename,
        business_purpose=business_purpose,
        business_function=business_function,
        business_area=business_area,
        production_targets=targets,
        inspection_sinks=inspection_sinks,
        upstream_producers=list(upstream_producers.values()),
        downstream_consumers=list(downstream_consumers.values()),
        shared_targets=shared_outputs_produced,
        shared_sources=shared_sources_consumed,
        dependency_position=position,
        deterministic_counts=counts,
        semantic_impact_signals=semantic_signals,
        operational_metadata=operational_metadata or {},
        deterministic_reference_score=det_crit.score,
        deterministic_reference_level=det_crit.level,
    )
