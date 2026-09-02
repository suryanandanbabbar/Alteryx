"""Authoritative business area vocabulary, definitions, and scope boundaries.

Shared single source of truth for:
- LLM prompt context builders
- Deterministic 7-tier classification hierarchy
- Portfolio materialization
- Coherence & conflict validation
"""

from __future__ import annotations

from dataclasses import dataclass


BUSINESS_AREA_TAXONOMY_VERSION: str = "3.0"


@dataclass(frozen=True)
class BusinessAreaDefinition:
    name: str
    scope: str
    included_activities: tuple[str, ...]
    excluded_activities: tuple[str, ...]
    boundary_rules: tuple[str, ...]
    representative_examples: tuple[str, ...]
    counterexamples: tuple[str, ...]


BUSINESS_AREA_DEFINITIONS: dict[str, BusinessAreaDefinition] = {
    "Underwriting": BusinessAreaDefinition(
        name="Underwriting",
        scope=(
            "Encompasses workflows that support risk assessment, policy evaluation, underwriting "
            "decisioning, pricing inputs, rating calculation, and coverage eligibility determination."
        ),
        included_activities=(
            "Policyholder risk assessment",
            "Policy eligibility determination and scoring",
            "Premium, pricing, and rating calculation",
            "Coverage evaluation and acceptance/rejection rules",
            "Underwriting guidelines and business rules execution",
            "Underwriting decision engine automation",
            "Loss experience modeling for premium pricing",
        ),
        excluded_activities=(
            "Claims intake, triage, and processing",
            "Claim adjudication and loss settlement",
            "Claims reserve calculation and allocation",
            "Claims fraud investigation",
            "Litigated claims reporting",
        ),
        boundary_rules=(
            "Workflows that calculate policy pricing, determine policy eligibility, evaluate risk appetite, "
            "or execute underwriting decisioning belong to Underwriting, even when consuming historical claims "
            "or loss experience data as supporting inputs.",
            "Supporting data domains (such as claims data inside an underwriting engine) do NOT alter the primary function.",
        ),
        representative_examples=(
            "Underwriting Decision Engine Application",
            "Policyholder Risk Scoring Pipeline",
            "Commercial Policy Rating & Premium Calculator",
            "Auto Coverage Eligibility Assessment",
        ),
        counterexamples=(
            "Claims Loss Reserve Calculator (belongs to Claims & Risk)",
            "Claims Fraud Detection Pipeline (belongs to Claims & Risk)",
            "Quarterly Claims Volume Extract (belongs to Claims & Risk)",
        ),
    ),
    "Claims & Risk": BusinessAreaDefinition(
        name="Claims & Risk",
        scope=(
            "Encompasses workflows that collectively analyse claims intake, triage, adjudication, "
            "loss reserves, indemnity and settlement payments, claims fraud, and litigation risk."
        ),
        included_activities=(
            "Claim intake, registration, and triage",
            "Claim adjudication, processing, and loss settlement",
            "Claims reserve estimation, allocation, and tracking",
            "Claims fraud detection and investigation prioritization",
            "Subrogation, salvage, and recovery operations",
            "Claims aging, severity, and loss portfolio analytics",
            "Statutory claims loss reporting",
        ),
        excluded_activities=(
            "Policy underwriting decisioning",
            "Policyholder coverage eligibility determination",
            "Initial policy pricing and rating calculation",
            "Sales territory commission distribution",
        ),
        boundary_rules=(
            "Workflows focused on handling, adjudicating, reserving, or investigating insurance claims "
            "belong to Claims & Risk. Mention of policyholder attributes or coverage limits as supporting "
            "context does not convert a claims workflow into Underwriting.",
        ),
        representative_examples=(
            "Claims Adjudication & Settlement Pipeline",
            "Claims Fraud Detection & Audit Model",
            "Outstanding Claims Reserve Calculator",
            "Litigated Claims Exposure Monitor",
        ),
        counterexamples=(
            "Underwriting Decision Engine (belongs to Underwriting, even if consuming claims submissions)",
            "Premium Experience Rating Calculator (belongs to Underwriting)",
        ),
    ),
    "Sales & Distribution": BusinessAreaDefinition(
        name="Sales & Distribution",
        scope=(
            "Encompasses workflows that support customer acquisition, product distribution, "
            "sales performance, agent/broker commissions, pipeline tracking, and commercial reporting."
        ),
        included_activities=(
            "Sales territory analytics and quota management",
            "Broker, agent, and producer commission calculation",
            "Distribution channel performance analysis",
            "Sales pipeline forecasting and opportunity tracking",
            "Customer and distributor commercial reporting",
            "Product sales volume and market distribution metrics",
        ),
        excluded_activities=(
            "Policy underwriting eligibility and risk scoring",
            "Claims handling and loss settlement",
            "Regulatory compliance audit reporting",
        ),
        boundary_rules=(
            "Workflows evaluating sales channels, producer performance, agent compensation, or commercial "
            "pipeline belong to Sales & Distribution, even when aggregating policy transaction records.",
        ),
        representative_examples=(
            "Sales Territory Performance Analytics",
            "Broker Commission & Incentive Calculation",
            "Commercial Distribution Pipeline Forecast",
            "Producer Quota & Channel Reconciliation",
        ),
        counterexamples=(
            "Underwriting Risk Scoring (belongs to Underwriting)",
            "Regulatory Compliance Filings (belongs to Legal)",
        ),
    ),
    "Legal": BusinessAreaDefinition(
        name="Legal",
        scope=(
            "Encompasses workflows supporting legal operations, court matter tracking, regulatory compliance "
            "filings, statutory reporting, contract analytics, and audit-mandated data processing."
        ),
        included_activities=(
            "Regulatory compliance reports and statutory insurance filings",
            "Legal matter tracking, court dockets, and case filings",
            "Subpoena and regulatory disclosure compilation",
            "Contract terms, policy clauses, and agreement analysis",
            "Corporate legal audit trail and compliance verification",
        ),
        excluded_activities=(
            "Operational claims adjusting and routine settlement",
            "Standard underwriting rating and premium quoting",
            "Sales commission distribution",
        ),
        boundary_rules=(
            "Workflows producing official regulatory compliance reports or supporting legal matter management "
            "belong to Legal, even when ingesting claims or policy transaction feeds.",
        ),
        representative_examples=(
            "Regulatory Compliance & Statutory Filing Pipeline",
            "Legal Matter & Litigation Tracking System",
            "Insurance Commissioner Regulatory Extract",
            "Corporate Contract Compliance Audit",
        ),
        counterexamples=(
            "Routine Claims Adjudication (belongs to Claims & Risk)",
            "Underwriting Rule Automation (belongs to Underwriting)",
        ),
    ),
    "Other / Unclassified": BusinessAreaDefinition(
        name="Other / Unclassified",
        scope=(
            "These workflows could not be confidently associated with a recognised "
            "business area based on the available workflow output evidence."
        ),
        included_activities=(
            "System log parsing and diagnostic monitoring",
            "Generic XML/JSON syntax formatting and sanitization",
            "Internal technical utility scripts",
        ),
        excluded_activities=(
            "Any workflow with an identifiable primary business function in Underwriting, Claims, Sales, or Legal.",
        ),
        boundary_rules=(
            "Use Other / Unclassified ONLY when no configured business area can reasonably own the workflow's "
            "primary business function based on available functional evidence.",
        ),
        representative_examples=(
            "Technical XML Log Parser Utility",
            "Database Schema Migration Test Harness",
        ),
        counterexamples=(
            "Any workflow with business deliverables in Underwriting, Claims, Sales, or Legal.",
        ),
    ),
}

ALLOWED_BUSINESS_AREAS: tuple[str, ...] = tuple(
    k for k in BUSINESS_AREA_DEFINITIONS.keys() if k != "Other / Unclassified"
)

BUSINESS_AREA_DESCRIPTIONS: dict[str, str] = {
    k: v.scope for k, v in BUSINESS_AREA_DEFINITIONS.items()
}
