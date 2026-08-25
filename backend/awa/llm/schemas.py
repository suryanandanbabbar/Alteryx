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
