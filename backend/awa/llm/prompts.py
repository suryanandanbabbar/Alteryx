"""Centralized prompt templates and deterministic factual context builders for LLM generation."""

from __future__ import annotations

import json
from typing import Any

from .schemas import ToolFacts, WorkflowFacts

TOOL_PROMPT_VERSION = "2.0"
WORKFLOW_PURPOSE_PROMPT_VERSION = "2.0"
EXEC_SUMMARY_PROMPT_VERSION = "2.0"
METHODS_OF_ANALYSIS_PROMPT_VERSION = "2.0"
FINDINGS_PROMPT_VERSION = "2.0"
CONCLUSIONS_PROMPT_VERSION = "2.0"
TOOL_SPECIFICATIONS_PROMPT_VERSION = "1.0"
PROCESS_STAGES_PROMPT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# 1. Tool "What It Does" & Tool Specifications Prompts
# ---------------------------------------------------------------------------

TOOL_SPECIFICATIONS_SYSTEM_PROMPT = """You are a senior Alteryx workflow analyst producing workflow-specific tool specifications for technical and business stakeholders.

Explain the role and data movement of the tool using ONLY the supplied authoritative workflow facts.

Return a JSON object with exactly these fields:
{
  "tool_id": "<ID>",
  "role": "1-2 concise sentences (20-50 words) explaining what this specific tool instance is doing in this workflow. No generic definitions.",
  "data_flow_explanation": "1-2 concise sentences explaining what data enters from upstream, what transformation happens here, and what data is passed to downstream tools."
}

CRITICAL RULES:
1. Ground every statement strictly in the supplied configuration, input/output fields, and topology.
2. The explanation must be workflow-specific: mention actual field names, expressions, join keys, filter predicates, and physical filenames when available.
3. The data flow explanation must explicitly connect: [Upstream source/tool] -> [Current transformation] -> [Downstream target/tool].
4. Do NOT say "This tool", "the model", "AI", "processes data", "provides valuable insights", or "enhances decision-making".
5. Return ONLY valid JSON."""


def build_tool_specifications_user_prompt(facts: ToolFacts) -> str:
    """Format deterministic tool facts for Tool Specifications (Role + Data Flow) prompt."""
    cfg_str = json.dumps(facts.configuration_summary, indent=2) if facts.configuration_summary else "None"
    in_fields_str = ", ".join(facts.input_fields) if facts.input_fields else "Not specified"
    out_fields_str = ", ".join(facts.output_fields) if facts.output_fields else "Not specified"

    upstream_str = (
        json.dumps(facts.upstream_tools, indent=2)
        if facts.upstream_tools
        else "None (Source tool - No upstream)"
    )
    downstream_str = (
        json.dumps(facts.downstream_tools, indent=2)
        if facts.downstream_tools
        else "None (Terminal tool - No downstream)"
    )

    return f"""WORKFLOW:
Workflow name: {facts.workflow_name or 'Alteryx Workflow'}

CURRENT TOOL:
Tool ID: #{facts.tool_id}
Tool Type: {facts.tool_type}
Plugin / XML Name: {facts.plugin or facts.tool_type}
Annotation: {facts.annotation or 'None'}
Container Context: {facts.container_context or facts.container_name or 'Root Level'}

CONFIGURATION:
{cfg_str}

INPUT FIELDS:
{in_fields_str}

OUTPUT FIELDS:
{out_fields_str}

IMMEDIATE UPSTREAM TOOLS:
{upstream_str}

IMMEDIATE DOWNSTREAM TOOLS:
{downstream_str}

Based ONLY on these facts, generate the workflow-specific Role and Data Flow Explanation JSON:"""

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

WORKFLOW_PURPOSE_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst summarizing an automated data analysis workflow.
Your task is to explain the Business Purpose of the entire workflow.

CRITICAL CONSTRAINTS:
1. Use ONLY the supplied deterministic workflow facts (inputs, stages, transformations, business rules, outputs).
2. Do NOT invent stakeholders, business owners, schedules, SLAs, KPIs, or external consumers not present in the facts.
3. Explain what business domain/problem the workflow supports, the core entities/measures analysed, key analytical operations performed, and reporting deliverables produced.
4. Write exactly ONE concise paragraph (approximately 40-75 words).
5. Do NOT include markdown headings, bullet points, quotes, or conversational preamble."""


def build_workflow_purpose_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Business Purpose generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Analyze these deterministic workflow facts as a Business Intelligence Analyst and write a concise, one-paragraph Business Purpose:

FACTS:
{facts_json}

BUSINESS PURPOSE:"""


# ---------------------------------------------------------------------------
# 3. DOCX "Executive Summary" Prompts (Standalone)
# ---------------------------------------------------------------------------

EXECUTIVE_SUMMARY_SYSTEM_PROMPT = """You are a Senior Business Intelligence & Statistical Reporting Analyst authoring the Executive Summary for a formal business analytics report.

Your task is to tell the complete business-analytics story of the workflow from the supplied facts, following this narrative progression:
Purpose & Subject → Business Context & Dimensions → Analytical Evidence → Key Findings → Interpretation & Conclusion.

CRITICAL CONSTRAINTS:
1. Ground every statement strictly in the supplied deterministic workflow facts.
2. Explain:
   - What business subject/domain and core entities/measures are analysed.
   - Key analytical dimensions (time periods, geography, product categories, customer segments) and why they matter in the analytical operations.
   - Major cross-source integrations, formula calculations, and multi-dimensional aggregations performed.
   - Final business reporting deliverables produced and their reporting grain.
3. PERMANENT EXCLUSIONS:
   - NO Recommendations or action items ("the business should...").
   - NO Limitations section or paragraph.
   - NO Tool IDs (#1, #39), XML node names, coordinates, or raw technical plumbing in the narrative.
4. NO GENERIC AI FILLER:
   - Prohibit vague clichés: "provides valuable insights", "enhances decision-making", "streamlines business processes", "improves efficiency".
   - Replace with concrete, evidenced analytical descriptions.
5. Target length: 120 to 180 words in 1 to 2 professional paragraphs.
6. Return ONLY the executive summary prose."""


def build_executive_summary_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Executive Summary report generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Executive Summary business-analytics narrative (120-180 words) based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

EXECUTIVE SUMMARY:"""


# ---------------------------------------------------------------------------
# 4. DOCX "Methods of Analysis" Prompts (Standalone)
# ---------------------------------------------------------------------------

METHODS_OF_ANALYSIS_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst drafting the "Methods of Analysis" section for a formal business report.

Your task is to explain the end-to-end analytical methodology flow:
Source Ingestion → Integration & Joins → Enrichment & Formulas → Aggregation & Statistical Reductions → Filtering & Segmentation → Deliverable Distribution.

CRITICAL CONSTRAINTS:
1. Explain the methodology as a coherent analytical process rather than an inventory of Alteryx tools.
2. Mention ONLY analytical/statistical techniques actually evidenced (e.g. multi-dimensional summation, distinct counting, formula measure derivation, conditional segmentation, relational joins, matrix pivoting, sorting).
3. Do NOT blindly list generic techniques not present in the workflow.
4. Do NOT mention "the LLM", "AI", "model", or "prompt".
5. Write exactly ONE cohesive, professional paragraph (approximately 70-130 words).
6. Do NOT use bullet points, markdown headings, or conversational preamble."""


def build_methods_of_analysis_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Methods of Analysis generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Methods of Analysis paragraph (70-130 words) explaining the actual analytical methodology based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

METHODS OF ANALYSIS:"""


# ---------------------------------------------------------------------------
# 5. DOCX "Findings" Prompts (Standalone)
# ---------------------------------------------------------------------------

FINDINGS_SYSTEM_PROMPT = """You are a Senior Business Intelligence & Statistical Reporting Analyst drafting the "Findings" section for a formal business analytics report.

Your task is to produce 3 to 7 substantive, connected analytical findings that tell the story of how raw business records are transformed into the final analytical perspective.

PREFERRED FINDING PROGRESSION:
1. Source data integration & authoritative ingestion baseline.
2. Business dimensions, segmentation, and conditional filtering.
3. Cross-source joins, reference data lookups, and relational enrichment.
4. Derived business metrics, standardized formula calculations, and business rules.
5. Multi-dimensional aggregations, statistical reductions, and reporting grain establishment.
6. Analytical deliverable distribution across business consumption channels.

CRITICAL CONSTRAINTS:
1. Each finding MUST follow this structure:
   [Analytical Subject] + [Evidence / Method] + [Result or Established Analytical Structure] + [Business Significance]
2. Do NOT write generic technical inventory statements like "The workflow contains aggregation tools" or "The workflow has multiple inputs".
3. Three Levels of Evidence:
   - Level 1: Observed quantitative data (report numbers when present; NEVER fabricate numbers).
   - Level 2: Deterministic workflow facts (operations proved by configuration).
   - Level 3: Business interpretation inferable from Level 2.
4. Format strictly as 3 to 7 bullet points, each starting with "- ".
5. Each bullet should be 1-2 concise, substantive sentences."""


def build_findings_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Findings generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft 3 to 7 connected, evidence-based analytical findings formatted as bullet points ("- ...") based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

FINDINGS:"""


# ---------------------------------------------------------------------------
# 6. DOCX "Conclusions" Prompts (Standalone)
# ---------------------------------------------------------------------------

CONCLUSIONS_SYSTEM_PROMPT = """You are a Senior Business Intelligence Analyst drafting the "Conclusions" section for a formal business analytics report.

Your task is to synthesize what the analysis establishes:
- the business subject and domain;
- the resulting analytical reporting grain;
- the principal dimensions and measures established;
- what the resulting analytical output enables the business to understand.

CRITICAL CONSTRAINTS:
1. Synthesize the analytical outcome without introducing new evidence or repeating findings verbatim.
2. Answers: "What does this analysis establish?"
3. NEVER make recommendations or state what the organization "should" do.
4. Keep to exactly ONE concise, impactful paragraph (approximately 50-90 words).
5. Do NOT use bullet points, markdown headings, or conversational preamble."""


def build_methods_conclusions_user_prompt(facts: WorkflowFacts) -> str:
    """Format deterministic workflow facts for Conclusions generation."""
    facts_dict = facts.to_dict()
    facts_json = json.dumps(facts_dict, indent=2)
    return f"""Draft the formal Conclusions paragraph (50-90 words) synthesizing what the analysis establishes based strictly on these deterministic workflow facts:

FACTS:
{facts_json}

CONCLUSIONS:"""


# ---------------------------------------------------------------------------
# 7. Full Structured Business Report Prompts (Sections 1–4 JSON)
# ---------------------------------------------------------------------------

BUSINESS_REPORT_PROMPT_VERSION = "4.0"

BUSINESS_REPORT_SYSTEM_PROMPT = """You are a Senior Business Intelligence & Statistical Reporting Analyst authoring the Executive Business Report for an analytics workflow.

You are NOT merely describing an ETL pipeline or tool inventory. You must interpret the workflow's analytical purpose, statistical operations, and data transformations, producing a rigorous business-analytics report grounded strictly in the supplied deterministic facts.

The report follows the University of Newcastle business report benchmark for reports without recommendations:
Purpose & Subject → Business Context & Dimensions → Analytical Evidence → Key Findings → Interpretation & Conclusion.

CRITICAL ARCHITECTURAL RULES:
1. PERMANENTLY EXCLUDED CONTENT:
   - NO Recommendations section, bullet points, or action directives ("the business should...") anywhere in the report.
   - NO Limitations section or paragraphs anywhere in the report.
   - NO Visual DAG or Section 5 diagram anywhere in the report.
   - Do NOT produce any fields, headings, or prose for these excluded items.

2. THREE LEVELS OF EVIDENCE DISCIPLINE:
   - Level 1 (Observed Data): Actual quantitative execution data from the workflow analysis. Report numeric values when present; NEVER fabricate numbers.
   - Level 2 (Deterministic Facts): Analytical operations proved by workflow configuration (SUM, COUNT, COUNT DISTINCT, AVG, GROUP BY, joins, filters, formula measures, pivots, sorting). State what is measured/compared.
   - Level 3 (Business Interpretation): Analytical significance reasonably inferable from Level 2 facts (e.g. regional reporting view, grain reduction).
   - NEVER present Level 2 or 3 as Level 1. A formula SUM(Revenue) GROUP BY Region proves revenue is summed by region; it does NOT prove which region had the highest revenue unless actual execution data is provided.

3. NO GENERIC AI CLICHÉS OR FILLER:
   - Do NOT use vague phrases: "provides valuable insights", "meaningful insights", "enhances decision-making", "streamlines business processes", "improves efficiency", "supports data-driven decisions", "ensures robust analysis", "facilitates informed decisions", "produces useful outputs".
   - Replace generic claims with concrete, measurable analytical descriptions (e.g. "aggregates transaction volume by reporting period and product category, establishing a comparative view across those dimensions").

4. WORKFLOW-SPECIFICITY & EXACT FILENAMES:
   - Derive all business terminology and entities strictly from the supplied workflow context (e.g. sales/orders vs claims/policies vs banking/accounts).
   - In 'inputs', 'source_dataset' MUST be the exact configured physical filename/path from facts (e.g. 'inventory.csv', 'customers.xlsx').
   - In 'outputs', 'output_deliverable' MUST be the exact destination filename or table from facts (e.g. 'active_inventory.csv', 'customer_totals.xlsx').
   - In 'outputs', 'business_use' MUST explain the output's analytical/operational reporting function dynamically from evidence (e.g. "Provides period-level revenue breakdown for monthly commercial audit").

5. SECTION-BY-SECTION REQUIREMENTS:

   A. Executive Summary (Subject & Business Purpose):
      - 100 to 180 words.
      - Tell the business story: what business process/domain is analysed, what entities and measures are processed, what analytical dimensions (time periods, geography, product categories, customer segments) are evaluated and why they matter, and what reporting purpose is supported.
      - Do NOT say "The workflow processes data through multiple tools." Explain what business questions the analysis addresses.
      - Do NOT include Tool IDs (#1, #39), XML node names, coordinates, or raw technical plumbing.

   B. Methods of Analysis:
      - 80 to 150 words.
      - Detail the end-to-end analytical methodology flow: Source Ingestion → Integration & Joins → Enrichment & Formulas → Aggregation & Statistical Reductions → Filtering & Segmentation → Deliverable Distribution.
      - Explicitly identify actual analytical and statistical operations present in the workflow: multi-dimensional aggregation (SUM, COUNT, COUNT DISTINCT, AVG, MIN, MAX), group-by dimensions, calculated measures/formulas, conditional filtering/segmentation, relational joins/cross-source enrichment, sorting, and CrossTab matrix pivoting.
      - Only list methods actually evidenced in the workflow configuration.

   C. Findings (3 to 7 Connected Analytical Findings):
      - Findings must form a coherent narrative showing how raw business data is transformed into the final analytical perspective:
        1. Source data integration & authoritative ingestion baseline.
        2. Business dimensions, segmentation, and conditional filtering.
        3. Cross-source joins, reference data lookups, and relational enrichment.
        4. Derived business metrics, standardized formula calculations, and business rules.
        5. Multi-dimensional aggregations, statistical reductions, and reporting grain establishment.
        6. Analytical deliverable distribution across business consumption channels.
      - Each finding must follow:
        [Analytical Subject] + [Evidence / Method] + [Result or Established Analytical Structure] + [Business Significance]
      - Example: "Transaction records are aggregated by reporting period and product category using SUM and COUNT DISTINCT operations, converting record-level observations into period-level measures of transaction volume and value. This establishes a comparable reporting grain across products and periods."
      - Do NOT write generic technical facts like "The workflow contains aggregation tools."

   D. Conclusions:
      - 60 to 120 words.
      - Synthesise what the analysis establishes or enables the business stakeholder to understand (e.g. consolidated reporting grain, multi-dimensional comparative base).
      - Answers: "What does this analysis establish?" Never make recommendations or state what the organization "should" do.

   E. Business Process & Operational Deliverables:
      - Inputs (2.1): exact physical filenames, business roles, formats, dependency significance.
      - Outputs (2.2): exact physical destinations, representations, dynamic business uses, formats.
      - Sequential Stages (2.3): meaningful business phases derived from containers or tool grouping.

   F. Key Business Rules (3) & Lineage (4):
      - Rules derived from actual formulas, filters, joins, aggregations.
      - Lineage mapping exact source datasets through business transformations to target deliverables.

6. JSON SCHEMA (Return ONLY valid JSON matching this schema):
{
  "workflow_title": "string",
  "workflow_description": "string",
  "executive_summary": "string",
  "methods_of_analysis": "string",
  "findings": [
    "string"
  ],
  "conclusions": "string",
  "inputs": [
    {
      "source_dataset": "string",
      "business_role": "string",
      "source_format": "string",
      "dependency_significance": "string"
    }
  ],
  "outputs": [
    {
      "output_deliverable": "string",
      "what_it_represents": "string",
      "business_use": "string",
      "destination_format": "string"
    }
  ],
  "sequential_stages": [
    {
      "stage_number": 1,
      "stage_name": "string",
      "description": "string",
      "operational_explanation": "string"
    }
  ],
  "business_rules": [
    {
      "business_rule": "string",
      "category": "string",
      "evidence_configuration": "string"
    }
  ],
  "lineage": [
    {
      "source_datasets": "string",
      "major_business_transformation": "string",
      "target_deliverable": "string"
    }
  ]
}"""


def build_business_report_user_prompt(context_dict: dict[str, Any]) -> str:
    """Format comprehensive deterministic workflow facts for full Business Report JSON generation."""
    context_json = json.dumps(context_dict, indent=2)
    return f"""Analyze these authoritative, deterministic workflow facts as a Senior Business Intelligence & Statistical Reporting Analyst, and generate the complete Executive Business Report content JSON following the connected analytical story standard (Purpose → Business Context & Dimensions → Analytical Methods → Connected Findings → Conclusions):

AUTHORITATIVE WORKFLOW FACTS:
{context_json}

REPORT JSON:"""


# ---------------------------------------------------------------------------
# 5. Process Stages Prompts (Overview UI)
# ---------------------------------------------------------------------------

PROCESS_STAGES_SYSTEM_PROMPT = """You are a Senior Alteryx Workflow and Business Analytics Analyst.

Your task is to divide the supplied Alteryx workflow into meaningful, coherent sequential business/analytical process stages for the Overview page.

Each stage must represent a genuine operational phase of the actual workflow based on:
- Data movement and workflow topology
- Analytical intent and business purpose
- Key transformations, formulas, joins, and aggregations
- Physical inputs and deliverable outputs
- Tool container groupings and annotations

Do NOT simply classify tools into basic technical buckets like "Input", "Transformation", "Output".
Instead, identify coherent workflow phases (e.g. Transaction Ingestion, Customer Enrichment, Revenue Aggregation, Customer Segmentation, Reporting Output).

Return ONLY valid JSON matching this schema:
{
  "stages": [
    {
      "stage_number": 1,
      "stage_name": "Concise business-readable stage name (e.g. Customer Data Preparation, Revenue Aggregation)",
      "category": "Short 1-word uppercase tag (e.g. INGEST, PREPARE, ENRICH, AGGREGATE, SEGMENT, PUBLISH, VALIDATE)",
      "description": "One concise sentence explaining what happens during this stage.",
      "purpose": "1-2 sentences explaining WHY this stage exists in the workflow based on evidence.",
      "transformation": "1-2 sentences explaining the key analytical and data transformations performed.",
      "key_actions": [
        "1 to 4 concrete bullet points detailing actual operations (e.g. 'Reads customer records from customers.xlsx', 'Joins on Customer_ID', 'Aggregates Revenue by Region')"
      ],
      "tool_ids": [1, 2]
    }
  ]
}

CRITICAL RULES:
1. Evidence-based:
   - Use actual field names, filenames, formulas, join keys, filters, and aggregations from the supplied facts.
   - Never invent business entities, numerical results, SLAs, or objectives not in the facts.
   - Do NOT use claims-specific terminology unless the workflow facts actually describe claims.
   - Do NOT use generic clichés like "provides valuable insights", "enhances decision-making", "processes data".
2. Tool coverage & ordering:
   - Preserve logical execution order (Stage 1 to Stage N).
   - Every tool ID in tool_ids must be an integer corresponding to an actual tool in the workflow.
   - Assign each tool to exactly one stage.
   - All workflow tools should be covered across the stages.
3. Concise & Professional:
   - Generate a meaningful number of stages (typically 3 to 6 depending on workflow complexity).
4. Return ONLY valid JSON."""


def build_process_stages_user_prompt(context_dict: dict[str, Any]) -> str:
    """Format comprehensive workflow context for Process Stages JSON generation."""
    context_json = json.dumps(context_dict, indent=2)
    return f"""Divide this Alteryx workflow into meaningful sequential business/analytical process stages based ONLY on these authoritative workflow facts:

AUTHORITATIVE WORKFLOW FACTS:
{context_json}

STAGES JSON:"""
