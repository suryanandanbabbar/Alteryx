"""Centralized prompt templates and deterministic factual context builders for LLM generation."""

from __future__ import annotations

import json
from typing import Any

from .schemas import ToolFacts, WorkflowFacts

TOOL_PROMPT_VERSION = "2.0"
WORKFLOW_PURPOSE_PROMPT_VERSION = "1.0"
EXEC_SUMMARY_PROMPT_VERSION = "1.0"
METHODS_OF_ANALYSIS_PROMPT_VERSION = "1.0"
FINDINGS_PROMPT_VERSION = "1.0"
CONCLUSIONS_PROMPT_VERSION = "1.0"
RECOMMENDATIONS_PROMPT_VERSION = "1.0"

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


# ---------------------------------------------------------------------------
# 4. DOCX "Methods of Analysis" Prompts
# ---------------------------------------------------------------------------

METHODS_OF_ANALYSIS_SYSTEM_PROMPT = """You are a lead enterprise analytics consultant drafting the "Methods of Analysis" subsection for a formal Workflow Assessment Report.

Your task is to explain the actual analytical process, data transformation methodology, and pipeline flow implemented by the workflow.

CRITICAL CONSTRAINTS:
1. Explain the methodology as a coherent end-to-end analytical process rather than as an inventory of Alteryx tools.
2. Mention ONLY analytical and data engineering techniques actually evidenced by the supplied facts (e.g. source ingestion, data consolidation, joins/reconciliation, aggregations, filtering/exclusion, calculated derivations, temporal analysis, segmentation, or deliverable preparation).
3. Do NOT blindly enumerate generic techniques that do not exist in the workflow.
4. Do NOT mention "the LLM", "AI", "model", or "prompt".
5. Write exactly ONE cohesive, professional paragraph (approximately 60-120 words).
6. Preferred style: "The workflow first ingests ..., then consolidates ... through ..., after which it derives ... and aggregates ... across ... . The resulting dataset is subsequently distributed into ... analytical outputs."
7. Do NOT use bullet points, markdown headings, or conversational preamble."""


def build_methods_of_analysis_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Methods of Analysis generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Methods of Analysis paragraph (60-120 words) explaining the actual transformation methodology based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

METHODS OF ANALYSIS:"""


# ---------------------------------------------------------------------------
# 5. DOCX "Findings" Prompts
# ---------------------------------------------------------------------------

FINDINGS_SYSTEM_PROMPT = """You are a senior data architect and management consultant drafting the "Findings" subsection of an Executive Summary for a formal Workflow Assessment Report.

Your task is to produce approximately 4 to 6 substantive, evidence-based findings grounded strictly in the supplied workflow facts.

CRITICAL CONSTRAINTS:
1. Every finding must be an objective observation supported directly by the workflow structure, inputs, processing stages, business rules, or deliverables.
2. Legitimate findings include:
   - multiple independent sources converging into a common analytical base
   - a central enriched dataset feeding several downstream branches
   - dependence on external file systems or specific storage formats
   - repeated aggregation, reconciliation, or multi-dimensional grouping patterns
   - specific business dimensions used for analysis and deliverable segmentation
   - critical data standardization, default values, or business calculation rules
   - operational dependencies or missing governance metadata visible in the workflow
3. Do NOT fabricate financial amounts, claim counts, transaction volumes, revenue, SLA percentages, execution frequencies, or external business outcomes not present in the facts.
4. Distinguish clearly between OBSERVED FACT and unsupported assumptions.
5. Format the output strictly as 4 to 6 bullet points, each starting with a bullet marker ("- ").
6. Each bullet should be 1-2 concise, substantive sentences explaining what was observed and why it matters analytically.
7. Do NOT include markdown headings, introductory sentences, or concluding notes."""


def build_findings_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Findings generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft 4 to 6 objective, evidence-based findings formatted as bullet points ("- ...") based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

FINDINGS:"""


# ---------------------------------------------------------------------------
# 6. DOCX "Conclusions" Prompts
# ---------------------------------------------------------------------------

CONCLUSIONS_SYSTEM_PROMPT = """You are a lead enterprise analytics consultant drafting the "Conclusions" subsection of an Executive Summary for a formal Workflow Assessment Report.

Your task is to write a concise executive-level synthesis explaining what the workflow fundamentally represents in the enterprise data architecture.

CRITICAL CONSTRAINTS:
1. Synthesize the overall workflow purpose, architectural pattern (e.g. centralized consolidation pipeline, multi-branch distribution pipeline, operational preparation layer), and operating model.
2. Address major architectural characteristics and overall process significance based strictly on the supplied facts.
3. Do NOT repeat the individual findings verbatim.
4. Do NOT introduce external facts or unsupported assumptions.
5. Keep this section shorter than Findings: exactly ONE concise, impactful paragraph (approximately 40-80 words).
6. Do NOT use bullet points, markdown headings, or conversational preamble."""


def build_methods_conclusions_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Conclusions generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Conclusions paragraph (40-80 words) synthesizing the workflow's architectural role based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

CONCLUSIONS:"""


# ---------------------------------------------------------------------------
# 7. DOCX "Recommendations" Prompts
# ---------------------------------------------------------------------------

RECOMMENDATIONS_SYSTEM_PROMPT = """You are an enterprise data management consultant drafting the "Recommendations" subsection of an Executive Summary for a formal Workflow Assessment Report.

Your task is to produce practical, actionable recommendations for business/process owners and migration teams based specifically on what was observed in this workflow.

CRITICAL CONSTRAINTS:
1. Every recommendation must be directly tied to observed characteristics of the workflow (e.g. validating undocumented business ownership, confirming production schedule/refresh dependencies, validating external file dependencies, standardizing business calculation rules, formalizing data lineage).
2. Do NOT produce generic platitudes like "Use AI to improve efficiency", "Improve data quality", or "Monitor the workflow regularly" unless tied to specific observed evidence.
3. Format the output strictly as 2 to 4 bullet points, each starting with a bullet marker ("- ").
4. Each bullet should be 1-2 concise, actionable sentences structured around: Action → Reason / Expected Benefit.
5. Do NOT include markdown headings, introductory sentences, or concluding notes."""


def build_recommendations_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Recommendations generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft 2 to 4 actionable, workflow-specific recommendations formatted as bullet points ("- ...") based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

RECOMMENDATIONS:"""
