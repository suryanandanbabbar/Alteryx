"""Business intelligence models for executive reporting and business process understanding.

Structured business facts that feed both Frontend and DOCX presentations.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any


@dataclass
class BusinessInput:
    """An input data source identified in the workflow."""
    tool_id: int
    name: str                       # e.g. "Claims Volume"
    raw_source: str                 # e.g. ".\\Data\\Claims_Volume_Extract_Demo.xlsx|||Sheet1$"
    source_type: str                # e.g. "Excel Workbook", "CSV Data File"
    source_filename: str | None = None  # e.g. "Claims_Volume_Extract_Demo.xlsx"
    sheet_or_table: str | None = None
    container_name: str | None = None
    business_role: str = ""         # e.g. "Primary claims dataset"
    dependency_significance: str = ""
    description: str = ""
    evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "raw_source": self.raw_source,
            "source_type": self.source_type,
            "source_filename": self.source_filename,
            "sheet_or_table": self.sheet_or_table,
            "container_name": self.container_name,
            "business_role": self.business_role,
            "dependency_significance": self.dependency_significance,
            "description": self.description,
            "evidence": self.evidence,
        }


@dataclass
class BusinessOutput:
    """An output dataset or report published by the workflow."""
    tool_id: int
    name: str                       # e.g. "Historical Claims Extract"
    raw_destination: str            # e.g. "Claims_Historical_Extract_Demo_Output.xlsx|||Detail"
    destination_type: str           # e.g. "Excel Workbook", "Alteryx Database"
    sheet_or_table: str | None = None
    business_meaning: str = ""      # e.g. "Claim-level historical reporting"
    likely_use: str = ""            # LLM-populated business use description
    business_purpose: str = ""      # Deprecated alias kept for backward compatibility
    container_name: str | None = None
    upstream_sources: list[str] = dc_field(default_factory=list)
    evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "raw_destination": self.raw_destination,
            "destination_type": self.destination_type,
            "sheet_or_table": self.sheet_or_table,
            "business_meaning": self.business_meaning or self.business_purpose,
            "likely_use": self.likely_use,
            "business_purpose": self.business_purpose or self.business_meaning,
            "container_name": self.container_name,
            "upstream_sources": self.upstream_sources,
            "evidence": self.evidence,
        }


@dataclass
class BusinessStage:
    """A high-level business processing stage derived from graph & containers."""
    stage_number: int
    name: str                       # Derived from workflow containers or tool-type grouping
    short_title: str                # e.g. "01 INGEST"
    summary: str                    # e.g. "Claims and supporting reference data"
    description: str
    business_purpose: str = ""
    major_transformation: str = ""
    tool_ids: list[int] = dc_field(default_factory=list)
    input_ids: list[int] = dc_field(default_factory=list)
    output_ids: list[int] = dc_field(default_factory=list)
    tool_count: int = 0
    container_name: str | None = None
    annotations: list[str] = dc_field(default_factory=list)
    transformations: list[str] = dc_field(default_factory=list)
    evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_number": self.stage_number,
            "name": self.name,
            "short_title": self.short_title,
            "summary": self.summary,
            "description": self.description,
            "business_purpose": self.business_purpose,
            "major_transformation": self.major_transformation,
            "tool_ids": self.tool_ids,
            "input_ids": self.input_ids,
            "output_ids": self.output_ids,
            "tool_count": self.tool_count,
            "container_name": self.container_name,
            "annotations": self.annotations,
            "transformations": self.transformations,
            "evidence": self.evidence,
        }


@dataclass
class BusinessTransformation:
    """A business-level transformation detected in the workflow."""
    category: str                   # e.g. "Aggregation", "Join / Enrichment", "Calculation / Derivation", "Classification / Aging", "Reshaping / Pivot", "Filtering / Selection", "Union / Combination", "Ordering / Prioritization"
    description: str                # Plain business language description
    affected_fields: list[str] = dc_field(default_factory=list)
    tool_ids: list[int] = dc_field(default_factory=list)
    evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "description": self.description,
            "affected_fields": self.affected_fields,
            "tool_ids": self.tool_ids,
            "evidence": self.evidence,
        }


@dataclass
class BusinessRule:
    """A promoted key business rule derived from tool configuration or annotations."""
    rule_name: str                  # e.g. "Payment Defaulting", "Activity Recency", "Aging Bucketing"
    category: str                   # e.g. "Calculation", "Aggregation", "Classification", "Data Cleansing"
    description: str                # Plain concrete sentence
    tool_ids: list[int] = dc_field(default_factory=list)
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "category": self.category,
            "description": self.description,
            "tool_ids": self.tool_ids,
            "evidence": self.evidence,
        }


@dataclass
class BusinessLineageEntry:
    """Source-to-target business lineage path."""
    source_name: str                # e.g. "Claims Volume"
    transformation: str             # e.g. "Aggregate by quarter/status"
    target_name: str                # e.g. "Quarter Summary"
    intermediate_stages: list[str] = dc_field(default_factory=list)
    transformation_summary: str = ""
    source_tool_id: int = 0
    target_tool_id: int = 0
    evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "transformation": self.transformation,
            "target_name": self.target_name,
            "intermediate_stages": self.intermediate_stages,
            "transformation_summary": self.transformation_summary,
            "source_tool_id": self.source_tool_id,
            "target_tool_id": self.target_tool_id,
            "evidence": self.evidence,
        }


@dataclass
class ExecutiveBusinessRule:
    """A business-significant rule with its operational meaning."""
    rule: str           # What the rule does in business terms
    meaning: str        # Why the rule matters to the resulting information

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "meaning": self.meaning,
        }


@dataclass
class ExecutiveSummaryContent:
    """Structured Executive Summary conforming to the business analysis report standard (no recommendations)."""
    subject_and_purpose: str = ""                       # 1. Subject matter / business purpose paragraph
    methods_and_process: str = ""                       # 2. Methods / analytical process flow paragraph
    findings: list[str] = dc_field(default_factory=list) # 3. Objective analytical findings
    conclusions: str = ""                               # 4. Business and analytical synthesis

    @property
    def purpose(self) -> str:
        return self.subject_and_purpose

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_and_purpose": self.subject_and_purpose,
            "methods_and_process": self.methods_and_process,
            "findings": self.findings,
            "conclusions": self.conclusions,
        }


@dataclass
class BusinessAssessment:
    """Governance, complexity, findings, gaps, disposition, and validation requirements."""
    complexity: str                 # "Low", "Moderate", "High", "Very High"
    complexity_reason: str
    complexity_factors: list[str] = dc_field(default_factory=list)
    platform: str = "Alteryx Designer"
    business_owner: str = "Not documented"
    schedule: str = "Not documented"
    criticality: str = "Not documented"
    documentation_quality: str = "Partially documented"
    assessment_status: str = "Automated assessment"
    key_observations: list[str] = dc_field(default_factory=list)
    key_activities: list[str] = dc_field(default_factory=list)
    key_findings: list[str] = dc_field(default_factory=list)
    role_and_value: list[str] = dc_field(default_factory=list)
    assessment_gaps: list[dict[str, str]] = dc_field(default_factory=list)
    preliminary_disposition: str = "Further assessment required"
    disposition_rationale: str = ""
    validation_checklist: list[str] = dc_field(default_factory=list)
    why_it_matters: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "complexity": self.complexity,
            "complexity_reason": self.complexity_reason,
            "complexity_factors": self.complexity_factors,
            "platform": self.platform,
            "business_owner": self.business_owner,
            "schedule": self.schedule,
            "criticality": self.criticality,
            "documentation_quality": self.documentation_quality,
            "assessment_status": self.assessment_status,
            "key_observations": self.key_observations,
            "key_activities": self.key_activities,
            "key_findings": self.key_findings,
            "role_and_value": self.role_and_value,
            "assessment_gaps": self.assessment_gaps,
            "preliminary_disposition": self.preliminary_disposition,
            "disposition_rationale": self.disposition_rationale,
            "validation_checklist": self.validation_checklist,
            "why_it_matters": self.why_it_matters,
        }


@dataclass
class WorkflowBusinessSummary:
    """The authoritative, deterministic business intelligence summary for the workflow."""
    business_purpose: str           # 1-3 concise sentences answering "Why does this workflow exist?"
    one_line_purpose: str           # e.g. "Business reporting and enrichment workflow"
    why_it_matters: str             # Factual business value summary
    source_inputs: list[BusinessInput] = dc_field(default_factory=list)
    processing_stages: list[BusinessStage] = dc_field(default_factory=list)
    transformations: list[BusinessTransformation] = dc_field(default_factory=list)
    business_rules: list[BusinessRule] = dc_field(default_factory=list)
    lineage: list[BusinessLineageEntry] = dc_field(default_factory=list)
    business_outputs: list[BusinessOutput] = dc_field(default_factory=list)
    assessment: BusinessAssessment = dc_field(default_factory=lambda: BusinessAssessment("Moderate", "Standard processing"))
    executive_summary: ExecutiveSummaryContent | None = None
    process_overview: str = ""      # Retained for compatibility
    information_flow: list[str] = dc_field(default_factory=list)
    overall_interpretation: str = ""
    evidence: list[str] = dc_field(default_factory=list)
    confidence_level: str = "High"
    business_function: str = ""
    business_area_tag: str = "UNCLASSIFIED"
    business_area_tag_source: str = ""
    business_area_taxonomy_version: str = "3.0"
    classification_conflict: bool = False
    classification_evidence: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "business_purpose": self.business_purpose,
            "business_function": self.business_function,
            "one_line_purpose": self.one_line_purpose,
            "why_it_matters": self.why_it_matters,
            "business_area_tag": self.business_area_tag,
            "business_area_tag_source": self.business_area_tag_source,
            "business_area_taxonomy_version": self.business_area_taxonomy_version,
            "classification_conflict": self.classification_conflict,
            "classification_evidence": self.classification_evidence,
            "source_inputs": [inp.to_dict() for inp in self.source_inputs],
            "processing_stages": [stg.to_dict() for stg in self.processing_stages],
            "transformations": [tr.to_dict() for tr in self.transformations],
            "business_rules": [br.to_dict() for br in self.business_rules],
            "lineage": [lin.to_dict() for lin in self.lineage],
            "business_outputs": [out.to_dict() for out in self.business_outputs],
            "assessment": self.assessment.to_dict(),
            "process_overview": self.process_overview,
            "information_flow": self.information_flow,
            "overall_interpretation": self.overall_interpretation,
            "evidence": self.evidence,
            "confidence_level": self.confidence_level,
        }
        if self.executive_summary is not None:
            d["executive_summary"] = self.executive_summary.to_dict()
        return d
