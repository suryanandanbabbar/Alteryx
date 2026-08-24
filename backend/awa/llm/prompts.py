"""Centralized prompt templates and deterministic factual context builders for LLM generation."""

from __future__ import annotations

import json
from typing import Any

from .schemas import ToolFacts, WorkflowFacts

TOOL_PROMPT_VERSION = "1.0"
WORKFLOW_PURPOSE_PROMPT_VERSION = "1.0"
EXEC_SUMMARY_PROMPT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# 1. Tool "What It Does" Prompts
# ---------------------------------------------------------------------------

TOOL_SYSTEM_PROMPT = """You are an expert enterprise ETL and Alteryx workflow analyst.
Your task is to generate a concise, factual, workflow-specific description answering "What It Does" for a single tool within an Alteryx workflow.

CRITICAL CONSTRAINTS:
1. Use ONLY the supplied deterministic workflow facts (configuration, role, upstream inputs, downstream targets, annotation).
2. Do NOT invent business objectives, stakeholders, schedules, SLAs, KPIs, or external systems not explicitly present in the facts.
3. Describe what THIS specific tool does in THIS workflow (referencing its actual columns, filters, aggregations, or targets).
4. Use clear, professional, business-readable language.
5. Write exactly ONE concise sentence (target 15-30 words).
6. Do NOT mention that an LLM generated this description.
7. Do NOT include markdown headings, bullet points, quotes, or conversational preamble."""


def build_tool_user_prompt(facts: ToolFacts) -> str:
    """Format deterministic tool facts for the LLM."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Analyze these deterministic facts for Tool #{facts.tool_id} ({facts.tool_type}) and write a one-sentence "What It Does" description:

FACTS:
{facts_json}

DESCRIPTION:"""


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
