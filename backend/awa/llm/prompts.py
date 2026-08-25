"""Centralized prompt templates and deterministic factual context builders for LLM generation."""

from __future__ import annotations

import json
from typing import Any

from .schemas import ToolFacts, WorkflowFacts

TOOL_PROMPT_VERSION = "2.0"
WORKFLOW_PURPOSE_PROMPT_VERSION = "1.0"
EXEC_SUMMARY_PROMPT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# 1. Tool "What It Does" Prompts (Workflow-Specific Role)
# ---------------------------------------------------------------------------

TOOL_SYSTEM_PROMPT = """You are an enterprise ETL workflow analyst.

Your task is to explain the role of ONE specific tool instance inside a larger ETL workflow.

Do NOT describe what the tool type generally does.

Instead, explain what THIS INSTANCE is doing in THIS WORKFLOW.

Use the supplied deterministic workflow facts as the source of truth.

The explanation must connect the tool's configuration and position in the data flow to its actual purpose in the workflow.

The reader is a business/technical stakeholder reviewing an existing ETL workflow before migration.

Rules:
- Describe the specific operation performed by this tool instance.
- Use actual fields, grouping, filtering, formulas, joins, outputs, or other configuration when available.
- Use upstream and downstream context to explain why the operation exists in the workflow.
- Use the annotation as supporting context.
- Use the workflow role as contextual information.
- Do not merely restate the tool type.
- Do not describe generic capabilities of the Alteryx tool.
- Do not invent business meaning not supported by the supplied facts.
- Do not mention that you are an AI or LLM.
- Do not say "this tool".
- Do not use vague phrases such as "processes the data" when the specific operation can be identified.
- Return ONE concise business-readable sentence or two short sentences.
- Target approximately 20-40 words.

CRITICAL:
The deterministic tool registry description is NOT the answer.
It is only background information about the tool type.
The answer must be workflow-specific."""


def build_tool_user_prompt(facts: ToolFacts) -> str:
    """Format deterministic tool facts for workflow-specific purpose prompt."""
    cfg_str = json.dumps(facts.configuration_summary, indent=2) if facts.configuration_summary else "None"
    in_fields_str = ", ".join(facts.input_fields) if facts.input_fields else "Not specified"
    out_fields_str = ", ".join(facts.output_fields) if facts.output_fields else "Not specified"

    upstream_str = (
        json.dumps(facts.upstream_tools, indent=2)
        if facts.upstream_tools
        else "None (Source tool)"
    )
    downstream_str = (
        json.dumps(facts.downstream_tools, indent=2)
        if facts.downstream_tools
        else "None (Terminal output)"
    )

    return f"""WORKFLOW:

Workflow name:
{facts.workflow_name or 'Alteryx Workflow'}

TOOL:

Tool ID:
{facts.tool_id}

Tool type:
{facts.tool_type}

Plugin:
{facts.plugin or facts.tool_type}

GENERIC TOOL DEFINITION:
{facts.deterministic_tool_definition or 'Standard ETL processing component.'}

WORKFLOW ROLE:
{facts.workflow_role}

ANNOTATION:
{facts.annotation or 'None'}

CONFIGURATION:
{cfg_str}

INPUT FIELDS:
{in_fields_str}

OUTPUT FIELDS:
{out_fields_str}

UPSTREAM TOOLS:
{upstream_str}

DOWNSTREAM TOOLS:
{downstream_str}

CONTAINER CONTEXT:
{facts.container_context or facts.container_name or 'None'}

Based ONLY on these facts, write the workflow-specific "What It Does" description for this particular tool instance.

Return only the final description."""


# ---------------------------------------------------------------------------
# 2. Workflow "Business Purpose" Prompts
# ---------------------------------------------------------------------------

WORKFLOW_PURPOSE_SYSTEM_PROMPT = """You are a senior enterprise data architect summarizing an automated data workflow.
Your task is to explain the Business Purpose of the entire workflow.

CRITICAL CONSTRAINTS:
1. Use ONLY the supplied deterministic workflow facts (inputs, stages, transformations, business rules, outputs).
2. Do NOT invent stakeholders, business owners, schedules, SLAs, KPIs, or external consumers not present in the facts.
3. Explain what business/process problem the workflow supports, the core data being processed, key transformations performed, and reporting deliverables produced.
4. Write exactly ONE concise paragraph (approximately 35-65 words).
5. Do NOT include markdown headings, bullet points, quotes, or conversational preamble."""


def build_workflow_purpose_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Business Purpose generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Analyze these deterministic workflow facts and write a concise, one-paragraph Business Purpose:

FACTS:
{facts_json}

BUSINESS PURPOSE:"""


# ---------------------------------------------------------------------------
# 3. DOCX "Executive Summary" Prompts
# ---------------------------------------------------------------------------

EXECUTIVE_SUMMARY_SYSTEM_PROMPT = """You are a lead enterprise analytics consultant drafting the Executive Summary section for a formal Alteryx Workflow Assessment and Migration Report.

CRITICAL CONSTRAINTS:
1. Use ONLY the supplied deterministic workflow facts.
2. Do NOT invent operational schedules, execution frequency, SLAs, ownership, performance metrics, or facts outside the analysis.
3. Summarize:
   - what the workflow accomplishes in its business domain
   - major source datasets integrated
   - primary transformations and derivations performed
   - final business deliverables generated
4. Target length: 100 to 150 words in 1 to 2 professional paragraphs.
5. Use professional consulting report tone.
6. Do NOT use bullet points, headings, greetings, or meta-commentary."""


def build_executive_summary_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Executive Summary report generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Executive Summary paragraph(s) (100-150 words) based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

EXECUTIVE SUMMARY:"""
