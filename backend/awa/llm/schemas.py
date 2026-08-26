"""Schemas for LLM facts extraction, prompt payloads, and narrative outputs."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Literal


@dataclass
class NarrativeResult:
    """A generated narrative text with provenance metadata."""
    text: str
    source: Literal["llm", "deterministic_fallback"]
    model: str = ""
    prompt_version: str = "2.0"
    is_cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "is_cached": self.is_cached,
        }


@dataclass
class ToolFacts:
    """Deterministic factual context for a single tool instance in an ETL workflow."""
    tool_id: int
    tool_type: str
    plugin: str
    tool_name: str
    workflow_name: str
    workflow_role: str
    annotation: str
    deterministic_tool_definition: str
    configuration_summary: dict[str, Any] = dc_field(default_factory=dict)
    input_fields: list[str] = dc_field(default_factory=list)
    output_fields: list[str] = dc_field(default_factory=list)
    upstream_tools: list[dict[str, Any]] = dc_field(default_factory=list)
    downstream_tools: list[dict[str, Any]] = dc_field(default_factory=list)
    container_name: str | None = None
    container_context: str | None = None
    raw_node_xml: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.workflow_name,
            "tool_id": self.tool_id,
            "tool_type": self.tool_type,
            "plugin": self.plugin,
            "tool_name": self.tool_name,
            "deterministic_tool_definition": self.deterministic_tool_definition,
            "workflow_role": self.workflow_role,
            "annotation": self.annotation,
            "configuration": self.configuration_summary,
            "input_fields": self.input_fields,
            "output_fields": self.output_fields,
            "upstream_tools": self.upstream_tools,
            "downstream_tools": self.downstream_tools,
            "container_context": self.container_context or self.container_name or "None",
        }


@dataclass
class WorkflowFacts:
    """Deterministic factual context for the entire workflow."""
    name: str
    version: str
    description: str
    total_tools: int
    source_inputs: list[dict[str, Any]] = dc_field(default_factory=list)
    processing_stages: list[dict[str, Any]] = dc_field(default_factory=list)
    major_transformations: list[str] = dc_field(default_factory=list)
    business_rules: list[str] = dc_field(default_factory=list)
    business_outputs: list[dict[str, Any]] = dc_field(default_factory=list)
    one_line_purpose: str = ""
    why_it_matters: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_name": self.name,
            "workflow_version": self.version,
            "description": self.description,
            "total_tools": self.total_tools,
            "source_inputs": self.source_inputs,
            "processing_stages": self.processing_stages,
            "major_transformations": self.major_transformations,
            "business_rules": self.business_rules,
            "business_outputs": self.business_outputs,
            "one_line_purpose": self.one_line_purpose,
            "why_it_matters": self.why_it_matters,
        }


@dataclass
class BusinessReportInputItem:
    source_dataset: str
    business_role: str
    source_format: str
    dependency_significance: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_dataset": self.source_dataset,
            "business_role": self.business_role,
            "source_format": self.source_format,
            "dependency_significance": self.dependency_significance,
        }


@dataclass
class BusinessReportOutputItem:
    output_deliverable: str
    what_it_represents: str
    business_use: str
    destination_format: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_deliverable": self.output_deliverable,
            "what_it_represents": self.what_it_represents,
            "business_use": self.business_use,
            "destination_format": self.destination_format,
        }


@dataclass
class BusinessReportStageItem:
    stage_number: int
    stage_name: str
    description: str
    operational_explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "description": self.description,
            "operational_explanation": self.operational_explanation,
        }


@dataclass
class BusinessReportRuleItem:
    business_rule: str
    category: str
    evidence_configuration: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "business_rule": self.business_rule,
            "category": self.category,
            "evidence_configuration": self.evidence_configuration,
        }


@dataclass
class BusinessReportLineageItem:
    source_datasets: str | list[str]
    major_business_transformation: str
    target_deliverable: str

    def to_dict(self) -> dict[str, Any]:
        srcs = self.source_datasets if isinstance(self.source_datasets, str) else " + ".join(self.source_datasets)
        return {
            "source_datasets": srcs,
            "major_business_transformation": self.major_business_transformation,
            "target_deliverable": self.target_deliverable,
        }


@dataclass
class BusinessReportContent:
    """Structured LLM-authored content for the complete Business Report."""
    workflow_title: str
    workflow_description: str
    executive_summary: str
    methods_of_analysis: str
    findings: list[str]
    conclusions: str
    inputs: list[BusinessReportInputItem] = dc_field(default_factory=list)
    outputs: list[BusinessReportOutputItem] = dc_field(default_factory=list)
    sequential_stages: list[BusinessReportStageItem] = dc_field(default_factory=list)
    business_rules: list[BusinessReportRuleItem] = dc_field(default_factory=list)
    lineage: list[BusinessReportLineageItem] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_title": self.workflow_title,
            "workflow_description": self.workflow_description,
            "executive_summary": self.executive_summary,
            "methods_of_analysis": self.methods_of_analysis,
            "findings": self.findings,
            "conclusions": self.conclusions,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "sequential_stages": [s.to_dict() for s in self.sequential_stages],
            "business_rules": [r.to_dict() for r in self.business_rules],
            "lineage": [l.to_dict() for l in self.lineage],
        }


@dataclass
class ComprehensiveWorkflowContext:
    """Authoritative facts extracted deterministically from CIR and DAG to ground the LLM."""
    workflow_name: str
    workflow_version: str
    workflow_description: str
    author: str
    total_tools: int
    total_connections: int
    inputs: list[dict[str, Any]] = dc_field(default_factory=list)
    outputs: list[dict[str, Any]] = dc_field(default_factory=list)
    containers: list[dict[str, Any]] = dc_field(default_factory=list)
    execution_steps: list[dict[str, Any]] = dc_field(default_factory=list)
    rules_and_formulas: list[dict[str, Any]] = dc_field(default_factory=list)
    lineage_traces: list[dict[str, Any]] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_metadata": {
                "name": self.workflow_name,
                "version": self.workflow_version,
                "description": self.workflow_description,
                "author": self.author,
                "total_tools": self.total_tools,
                "total_connections": self.total_connections,
            },
            "inputs": self.inputs,
            "outputs": self.outputs,
            "containers": self.containers,
            "execution_steps": self.execution_steps,
            "rules_and_formulas": self.rules_and_formulas,
            "lineage_traces": self.lineage_traces,
        }


@dataclass
class ProcessStageContent:
    """Structured LLM-authored content for an individual process stage."""
    stage_number: int
    stage_name: str
    category: str
    description: str
    purpose: str
    transformation: str
    key_actions: list[str] = dc_field(default_factory=list)
    tool_ids: list[int] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_number": self.stage_number,
            "stage_name": self.stage_name,
            "category": self.category,
            "description": self.description,
            "purpose": self.purpose,
            "transformation": self.transformation,
            "key_actions": self.key_actions,
            "tool_ids": self.tool_ids,
        }


@dataclass
class WorkflowProcessStages:
    """Collection of LLM-generated process stages for a workflow."""
    stages: list[ProcessStageContent] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stages": [s.to_dict() for s in self.stages],
        }

