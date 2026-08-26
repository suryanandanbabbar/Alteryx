"""Deterministic facts extraction and narrative generation service with validation and fallback."""

from __future__ import annotations

import logging
import re
from typing import Any
import networkx as nx

from awa.model.workflow import Workflow
from awa.model.tool import Tool
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.visual_category import get_visual_category
from awa.tools.catalog import get_tool_summary
from awa.tools import humanize_tool_configuration

from .client import LLMClient, get_default_llm_client
from .schemas import (
    NarrativeResult,
    ToolFacts,
    WorkflowFacts,
    BusinessReportContent,
    BusinessReportInputItem,
    BusinessReportOutputItem,
    BusinessReportStageItem,
    BusinessReportRuleItem,
    BusinessReportLineageItem,
    ComprehensiveWorkflowContext,
)
from .prompts import (
    TOOL_PROMPT_VERSION,
    WORKFLOW_PURPOSE_PROMPT_VERSION,
    EXEC_SUMMARY_PROMPT_VERSION,
    METHODS_OF_ANALYSIS_PROMPT_VERSION,
    FINDINGS_PROMPT_VERSION,
    CONCLUSIONS_PROMPT_VERSION,
    BUSINESS_REPORT_PROMPT_VERSION,
    TOOL_SYSTEM_PROMPT,
    WORKFLOW_PURPOSE_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    METHODS_OF_ANALYSIS_SYSTEM_PROMPT,
    FINDINGS_SYSTEM_PROMPT,
    CONCLUSIONS_SYSTEM_PROMPT,
    BUSINESS_REPORT_SYSTEM_PROMPT,
    build_tool_user_prompt,
    build_workflow_purpose_user_prompt,
    build_executive_summary_user_prompt,
    build_methods_of_analysis_user_prompt,
    build_findings_user_prompt,
    build_methods_conclusions_user_prompt,
    build_business_report_user_prompt,
)
from .cache import LLMNarrativeCache, get_global_narrative_cache, compute_cache_key

logger = logging.getLogger("awa.llm")


def _get_workflow_role(tool_type: str, category: str) -> str:
    """Map tool type and visual category to standard workflow role."""
    t_lower = tool_type.lower()
    c_lower = category.lower()

    if "sort" in t_lower:
        return "Ordering"
    if "select" in t_lower:
        return "Field Selection"
    if "unique" in t_lower:
        return "Deduplication"
    if "sample" in t_lower:
        return "Sampling"
    if "datetime" in t_lower:
        return "Temporal Formatting"
    if any(k in t_lower for k in ("regex", "texttocolumns", "xmlparse", "jsonparse")):
        return "Data Parsing"
    if any(k in t_lower for k in ("input", "fileinput", "directory")):
        return "Data Input"
    if any(k in t_lower for k in ("output", "browse")):
        return "Data Output"
    if any(k in t_lower for k in ("blockuntildone", "message", "test")):
        return "Execution Control"

    if c_lower == "input":
        return "Data Input"
    if c_lower == "output":
        return "Data Output"
    if c_lower == "join":
        return "Data Integration"
    if c_lower == "filter":
        return "Data Filtering"
    if c_lower in ("formula", "transform", "cleansing"):
        return "Data Transformation"
    if c_lower in ("summarize", "aggregate"):
        return "Aggregation"
    if c_lower == "sort":
        return "Ordering"
    if c_lower == "select":
        return "Field Selection"
    if c_lower == "unique":
        return "Deduplication"

    return "Data Transformation"


def _clean_narrative_text(raw_text: str | None) -> str:
    """Clean and sanitize model generated text."""
    if not raw_text:
        return ""
    text = raw_text.strip()

    # Remove markdown codeblock fences if returned
    if text.startswith("```") and text.endswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()

    # Remove wrapping quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()

    # Remove common preamble prefixes
    prefixes_to_strip = [
        r"^what it does:\s*",
        r"^here is the summary:\s*",
        r"^here is the description:\s*",
        r"^here is (?:a|the) (?:concise )?(?:one-sentence )?(?:description|summary).*?:\s*",
        r"^business purpose:\s*",
        r"^executive summary:\s*",
        r"^methods of analysis:\s*",
        r"^findings:\s*",
        r"^conclusions:\s*",
        r"^recommendations:\s*",
        r"^description:\s*",
        r"^summary:\s*",
        r"^this tool\s+",
    ]
    for pattern in prefixes_to_strip:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    # Capitalize first character if lowercase
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text


def extract_tool_facts(workflow: Workflow, tool: Tool, graph: nx.DiGraph | None = None) -> ToolFacts:
    """Extract deterministic facts for a single tool instance from the workflow model and DAG."""
    upstreams: list[dict[str, Any]] = []
    downstreams: list[dict[str, Any]] = []
    input_fields: list[str] = []

    if graph is not None:
        if graph.has_node(tool.tool_id):
            for pred_id in graph.predecessors(tool.tool_id):
                pred_tool = workflow.tools.get(pred_id)
                if pred_tool:
                    upstreams.append({
                        "tool_id": pred_id,
                        "tool_type": pred_tool.tool_type,
                        "name": pred_tool.name or pred_tool.tool_type,
                        "annotation": pred_tool.annotation,
                    })
                    for f in pred_tool.output_fields:
                        if f.name and f.name not in input_fields:
                            input_fields.append(f.name)
            for succ_id in graph.successors(tool.tool_id):
                succ_tool = workflow.tools.get(succ_id)
                if succ_tool:
                    downstreams.append({
                        "tool_id": succ_id,
                        "tool_type": succ_tool.tool_type,
                        "name": succ_tool.name or succ_tool.tool_type,
                        "annotation": succ_tool.annotation,
                    })

    raw_cfg = tool.configuration.parsed if tool.configuration else {}
    cleaned_cfg = humanize_tool_configuration(tool.tool_type, raw_cfg)
    tech_function = get_tool_summary(tool.plugin or tool.tool_type)
    output_flds = [f.name for f in tool.output_fields if f.name]
    vis_cat = get_visual_category(tool.tool_type)
    role = _get_workflow_role(tool.tool_type, vis_cat)
    container_ctx = tool.container_name if tool.container_name else "Root Level (No Container)"

    return ToolFacts(
        tool_id=tool.tool_id,
        tool_type=tool.tool_type,
        plugin=tool.plugin or tool.tool_type,
        tool_name=tool.name or tool.tool_type,
        workflow_name=workflow.metadata.name or "Alteryx Workflow",
        workflow_role=role,
        annotation=tool.annotation,
        deterministic_tool_definition=tech_function,
        configuration_summary=cleaned_cfg,
        input_fields=input_fields,
        output_fields=output_flds,
        upstream_tools=upstreams,
        downstream_tools=downstreams,
        container_name=tool.container_name,
        container_context=container_ctx,
        raw_node_xml=tool.raw_node_xml,
    )


def extract_workflow_facts(workflow: Workflow, business_summary: WorkflowBusinessSummary) -> WorkflowFacts:
    """Extract deterministic workflow facts for business purpose, executive summary, and DOCX sections."""
    source_inputs: list[dict[str, Any]] = [
        {
            "name": inp.name,
            "source": inp.raw_source,
            "type": inp.source_type,
            "business_role": inp.business_role,
        }
        for inp in business_summary.source_inputs
    ]

    stages: list[dict[str, Any]] = [
        {
            "stage_number": stg.stage_number,
            "name": stg.name,
            "summary": stg.summary,
            "tool_count": stg.tool_count,
            "transformations": stg.transformations,
        }
        for stg in business_summary.processing_stages
    ]

    major_trans = [
        tr.description
        for tr in business_summary.transformations
        if tr.description
    ]

    rules = [
        br.description or br.rule_name
        for br in business_summary.business_rules
        if br.description or br.rule_name
    ]

    outputs: list[dict[str, Any]] = [
        {
            "name": out.name,
            "destination": out.raw_destination,
            "destination_type": out.destination_type,
            "business_meaning": out.business_meaning or out.business_purpose,
        }
        for out in business_summary.business_outputs
    ]

    return WorkflowFacts(
        name=workflow.metadata.name or "Alteryx Workflow",
        version=workflow.metadata.version or "2024.1",
        description=workflow.metadata.description or "",
        total_tools=len(workflow.tools),
        source_inputs=source_inputs,
        processing_stages=stages,
        major_transformations=major_trans,
        business_rules=rules,
        business_outputs=outputs,
        one_line_purpose=business_summary.one_line_purpose or "",
        why_it_matters=business_summary.why_it_matters or "",
    )


def extract_comprehensive_workflow_context(
    workflow: Workflow,
    business_summary: WorkflowBusinessSummary,
    graph: nx.DiGraph | None = None,
) -> ComprehensiveWorkflowContext:
    """Extract rich, authoritative workflow context from CIR, tools, formulas, and graph topology."""
    inputs_list = []
    for inp in business_summary.source_inputs:
        inputs_list.append({
            "tool_id": inp.tool_id,
            "canonical_filename": inp.source_filename or inp.name,
            "raw_path": inp.raw_source,
            "source_type": inp.source_type,
            "sheet_or_table": inp.sheet_or_table,
            "container": inp.container_name,
        })

    outputs_list = []
    for out in business_summary.business_outputs:
        outputs_list.append({
            "tool_id": out.tool_id,
            "canonical_destination": out.sheet_or_table or out.name,
            "raw_path": out.raw_destination,
            "destination_type": out.destination_type,
            "upstream_sources": out.upstream_sources,
            "container": out.container_name,
        })

    containers_list = []
    for cid, cont in sorted(workflow.containers.items()):
        c_tools = [t.tool_id for t in workflow.tools.values() if t.container_id == cid]
        containers_list.append({
            "container_id": cid,
            "caption": cont.caption,
            "disabled": cont.disabled,
            "tool_ids": c_tools,
        })

    steps_list = []
    rules_and_formulas = []
    for tid, tool in sorted(workflow.tools.items()):
        cfg = tool.configuration.parsed or {}
        cleaned_cfg = humanize_tool_configuration(tool.tool_type, cfg)
        steps_list.append({
            "tool_id": tid,
            "tool_type": tool.tool_type,
            "name": tool.name or tool.tool_type,
            "annotation": tool.annotation,
            "container": tool.container_name,
            "configuration": cleaned_cfg,
        })

        # Extract explicit analytical and statistical operations
        if tool.tool_type in ("Formula", "MultiFieldFormula"):
            for ff in cfg.get("formula_fields", []):
                rules_and_formulas.append({
                    "tool_id": tid,
                    "type": "Formula Calculation",
                    "field": ff.get("field"),
                    "expression": ff.get("expression"),
                    "formula_type": ff.get("type", "String"),
                })
        elif tool.tool_type == "Filter":
            rules_and_formulas.append({
                "tool_id": tid,
                "type": "Filter Predicate",
                "expression": cfg.get("expression") or cfg.get("Expression") or "",
                "predicate_details": cfg.get("filter_predicate", ""),
            })
        elif tool.tool_type == "Join":
            rules_and_formulas.append({
                "tool_id": tid,
                "type": "Join Criteria",
                "join_fields": cfg.get("join_fields"),
                "left_keys": cfg.get("left_keys", []),
                "right_keys": cfg.get("right_keys", []),
            })
        elif tool.tool_type == "Summarize":
            summarize_entries = []
            for sf in cfg.get("summarize_fields", []):
                summarize_entries.append({
                    "field": sf.get("field", ""),
                    "action": sf.get("action", ""),
                    "rename": sf.get("rename", ""),
                })
            rules_and_formulas.append({
                "tool_id": tid,
                "type": "Summarize Aggregation",
                "operations": summarize_entries,
                "raw_fields": cfg.get("summarize_fields"),
            })
        elif tool.tool_type == "CrossTab":
            rules_and_formulas.append({
                "tool_id": tid,
                "type": "CrossTab Pivot",
                "group_fields": cfg.get("group_fields", []),
                "header_field": cfg.get("header_field"),
                "data_field": cfg.get("data_field"),
                "aggregation_methods": cfg.get("methods", []),
            })
        elif tool.tool_type == "Sort":
            rules_and_formulas.append({
                "tool_id": tid,
                "type": "Sort Ordering",
                "sort_fields": cfg.get("sort_fields", []),
            })
        elif tool.tool_type == "AlteryxSelect":
            select_fields = cfg.get("select_fields", [])
            if select_fields:
                rules_and_formulas.append({
                    "tool_id": tid,
                    "type": "Field Selection & Renaming",
                    "fields_count": len(select_fields),
                })

    lineage_traces = []
    for lin in business_summary.lineage:
        lineage_traces.append({
            "source": lin.source_name,
            "target": lin.target_name,
            "summary": lin.transformation_summary or lin.transformation,
        })

    return ComprehensiveWorkflowContext(
        workflow_name=workflow.metadata.name or "Alteryx Workflow",
        workflow_version=workflow.metadata.version or "2024.1",
        workflow_description=workflow.metadata.description or "",
        author=workflow.metadata.author or "Not documented",
        total_tools=len(workflow.tools),
        total_connections=len(workflow.connections),
        inputs=inputs_list,
        outputs=outputs_list,
        containers=containers_list,
        execution_steps=steps_list,
        rules_and_formulas=rules_and_formulas,
        lineage_traces=lineage_traces,
    )


class LLMNarrativeGenerator:
    """High-level orchestration service for narrative generation with caching and fallback."""

    def __init__(
        self,
        client: LLMClient | None = None,
        cache: LLMNarrativeCache | None = None,
    ) -> None:
        self._client = client
        self._cache = cache or get_global_narrative_cache()

    @property
    def client(self) -> LLMClient:
        return self._client or get_default_llm_client()

    def get_cached_tool_summary(
        self,
        workflow: Workflow,
        tool: Tool,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> NarrativeResult | None:
        """Check if a tool summary is already cached without triggering LLM generation."""
        facts = extract_tool_facts(workflow, tool, graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key=f"tool_{tool.tool_id}",
            prompt_version=TOOL_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )
        return self._cache.get(cache_key)

    def generate_tool_summary(
        self,
        workflow: Workflow,
        tool: Tool,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate a workflow-specific 'What It Does' summary for a tool instance."""
        fallback_text = get_tool_summary(tool.plugin or tool.tool_type)

        facts = extract_tool_facts(workflow, tool, graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key=f"tool_{tool.tool_id}",
            prompt_version=TOOL_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info(
                "[LLM CACHE] type=tool_summary tool_id=%d status=HIT",
                tool.tool_id,
            )
            return cached

        logger.info(
            "[LLM CACHE] type=tool_summary tool_id=%d status=MISS",
            tool.tool_id,
        )

        system_prompt = TOOL_SYSTEM_PROMPT
        user_prompt = build_tool_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt)
        cleaned = _clean_narrative_text(raw_response)

        if cleaned and len(cleaned.split()) >= 3 and len(cleaned) <= 500:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=TOOL_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info(
                "[LLM] tool_summary stored in cache tool_id=%d text_len=%d",
                tool.tool_id, len(cleaned),
            )
            return result

        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=TOOL_PROMPT_VERSION,
        )
        return fallback_result

    def generate_business_purpose(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate a workflow-level Business Purpose description for Overview."""
        fallback_text = business_summary.business_purpose or "Automated ETL and data preparation workflow."

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="business_purpose",
            prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=business_purpose status=HIT")
            return cached

        logger.info("[LLM CACHE] type=business_purpose status=MISS")

        system_prompt = WORKFLOW_PURPOSE_SYSTEM_PROMPT
        user_prompt = build_workflow_purpose_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt)
        cleaned = _clean_narrative_text(raw_response)

        if cleaned and len(cleaned.split()) >= 10 and len(cleaned) <= 800:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info("[LLM] business_purpose stored in cache text_len=%d", len(cleaned))
            return result

        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
        )
        return fallback_result

    def generate_executive_summary(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate an Executive Summary narrative for the DOCX report."""
        fallback_text = (
            business_summary.executive_summary.subject_and_purpose
            if business_summary.executive_summary and business_summary.executive_summary.subject_and_purpose
            else (business_summary.business_purpose or "This report details the automated data preparation workflow.")
        )

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="executive_summary",
            prompt_version=EXEC_SUMMARY_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=executive_summary status=HIT")
            return cached

        logger.info("[LLM CACHE] type=executive_summary status=MISS")

        system_prompt = EXECUTIVE_SUMMARY_SYSTEM_PROMPT
        user_prompt = build_executive_summary_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=600)
        cleaned = _clean_narrative_text(raw_response)

        if cleaned and len(cleaned.split()) >= 20 and len(cleaned) <= 1500:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=EXEC_SUMMARY_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info("[LLM] executive_summary stored in cache text_len=%d", len(cleaned))
            return result

        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=EXEC_SUMMARY_PROMPT_VERSION,
        )
        return fallback_result

    def generate_methods_of_analysis(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate Methods of Analysis methodology narrative for DOCX report."""
        fallback_text = (
            business_summary.executive_summary.methods_and_process
            if business_summary.executive_summary and business_summary.executive_summary.methods_and_process
            else "The workflow applies sequential data preparation, validation, and calculation rules to produce analysis-ready records."
        )

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="methods_of_analysis",
            prompt_version=METHODS_OF_ANALYSIS_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=methods_of_analysis status=HIT")
            return cached

        logger.info("[LLM CACHE] type=methods_of_analysis status=MISS")

        system_prompt = METHODS_OF_ANALYSIS_SYSTEM_PROMPT
        user_prompt = build_methods_of_analysis_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=500)
        cleaned = _clean_narrative_text(raw_response)

        if cleaned and len(cleaned.split()) >= 15 and len(cleaned) <= 1200:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=METHODS_OF_ANALYSIS_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info("[LLM] methods_of_analysis stored in cache text_len=%d", len(cleaned))
            return result

        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=METHODS_OF_ANALYSIS_PROMPT_VERSION,
        )
        return fallback_result

    def generate_findings(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        workflow_id: str = "",
    ) -> list[str]:
        """Generate 4-6 evidence-based findings for DOCX report."""
        fallback_findings = (
            business_summary.executive_summary.findings
            if business_summary.executive_summary and business_summary.executive_summary.findings
            else ["The workflow consolidates source data into structured operational deliverables."]
        )

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="findings",
            prompt_version=FINDINGS_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=findings status=HIT")
            # Items stored in cached.text as JSON list or newline-separated
            try:
                import json
                return json.loads(cached.text)
            except Exception:
                return [line.strip("- *• ") for line in cached.text.split("\n") if line.strip("- *• ")]

        logger.info("[LLM CACHE] type=findings status=MISS")

        system_prompt = FINDINGS_SYSTEM_PROMPT
        user_prompt = build_findings_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=700)
        cleaned = _clean_narrative_text(raw_response)

        # Parse bullet points from response
        bullet_items = []
        if cleaned:
            for line in cleaned.split("\n"):
                stripped = line.strip()
                if stripped.startswith(("-", "*", "•")):
                    item_text = re.sub(r"^[-*•]\s*", "", stripped).strip()
                    if item_text and len(item_text) > 10:
                        bullet_items.append(item_text)
                elif re.match(r"^\d+[\.\)]\s+", stripped):
                    item_text = re.sub(r"^\d+[\.\)]\s+", "", stripped).strip()
                    if item_text and len(item_text) > 10:
                        bullet_items.append(item_text)

        if len(bullet_items) >= 2:
            import json
            result = NarrativeResult(
                text=json.dumps(bullet_items),
                source="llm",
                model=self.client.model_name,
                prompt_version=FINDINGS_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info("[LLM] findings stored in cache items_count=%d", len(bullet_items))
            return bullet_items

        logger.info("[LLM] findings fallback to deterministic items_count=%d", len(fallback_findings))
        return fallback_findings

    def generate_conclusions(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate Conclusions synthesis narrative for DOCX report."""
        fallback_text = (
            business_summary.executive_summary.conclusions
            if business_summary.executive_summary and business_summary.executive_summary.conclusions
            else "The workflow operates as a standardized data preparation process transforming source records into structured outputs."
        )

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="conclusions",
            prompt_version=CONCLUSIONS_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=conclusions status=HIT")
            return cached

        logger.info("[LLM CACHE] type=conclusions status=MISS")

        system_prompt = CONCLUSIONS_SYSTEM_PROMPT
        user_prompt = build_methods_conclusions_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=400)
        cleaned = _clean_narrative_text(raw_response)

        if cleaned and len(cleaned.split()) >= 10 and len(cleaned) <= 800:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=CONCLUSIONS_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.info("[LLM] conclusions stored in cache text_len=%d", len(cleaned))
            return result

        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=CONCLUSIONS_PROMPT_VERSION,
        )
        return fallback_result



    def generate_business_report(
        self,
        workflow: Workflow,
        business_summary: WorkflowBusinessSummary,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> BusinessReportContent | None:
        """Generate full, structured, LLM-authored Business Report content."""
        context = extract_comprehensive_workflow_context(workflow, business_summary, graph=graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="business_report_full",
            prompt_version=BUSINESS_REPORT_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=context.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=business_report_full status=HIT")
            try:
                import json
                data = json.loads(cached.text)
                return self._parse_business_report_json(data)
            except Exception as e:
                logger.warning("[LLM CACHE] Failed to deserialize cached business report: %s", e)

        logger.info("[LLM CACHE] type=business_report_full status=MISS")

        system_prompt = BUSINESS_REPORT_SYSTEM_PROMPT
        user_prompt = build_business_report_user_prompt(context.to_dict())
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=2500)

        if not raw_response:
            logger.warning("[LLM] Business report generation returned empty response")
            return None

        # Clean response and parse JSON
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()

        try:
            import json
            data = json.loads(cleaned)
            report = self._parse_business_report_json(data)
            if report:
                result = NarrativeResult(
                    text=json.dumps(report.to_dict()),
                    source="llm",
                    model=self.client.model_name,
                    prompt_version=BUSINESS_REPORT_PROMPT_VERSION,
                )
                self._cache.set(cache_key, result)
                logger.info("[LLM] Business report successfully generated and cached")
                return report
        except Exception as exc:
            logger.warning("[LLM] Failed to parse Business Report JSON response: %s", exc)

        return None

    def _parse_business_report_json(self, data: dict[str, Any]) -> BusinessReportContent | None:
        """Validate and map dictionary to BusinessReportContent with analytical quality checks."""
        try:
            # 1. Reject prohibited keys
            if "recommendations" in data or "limitations" in data or "visual_dag" in data or "section_5" in data:
                logger.warning("[LLM] Business report JSON contained permanently excluded keys; stripping them")

            exec_summary = str(data.get("executive_summary", "")).strip()
            methods_analysis = str(data.get("methods_of_analysis", "")).strip()
            conclusions = str(data.get("conclusions", "")).strip()

            # Reject empty core analytical sections
            if not exec_summary or len(exec_summary) < 20:
                logger.warning("[LLM] Validation failed: executive_summary is too short or empty")
                return None
            if not methods_analysis or len(methods_analysis) < 20:
                logger.warning("[LLM] Validation failed: methods_of_analysis is too short or empty")
                return None
            if not conclusions or len(conclusions) < 15:
                logger.warning("[LLM] Validation failed: conclusions is too short or empty")
                return None

            # 2. Parse and validate findings (3 to 7 items expected, minimum 1)
            raw_findings = data.get("findings", [])
            findings = [str(f).strip() for f in raw_findings if str(f).strip()]
            if not findings:
                logger.warning("[LLM] Validation failed: findings list is empty")
                return None

            # 3. Parse and validate inputs
            inputs = [
                BusinessReportInputItem(
                    source_dataset=str(i.get("source_dataset", "")).strip(),
                    business_role=str(i.get("business_role", "")).strip(),
                    source_format=str(i.get("source_format", "")).strip(),
                    dependency_significance=str(i.get("dependency_significance", "")).strip(),
                )
                for i in data.get("inputs", [])
                if str(i.get("source_dataset", "")).strip()
            ]

            # 4. Parse and validate outputs (must have business_use)
            outputs = [
                BusinessReportOutputItem(
                    output_deliverable=str(o.get("output_deliverable", "")).strip(),
                    what_it_represents=str(o.get("what_it_represents", "")).strip(),
                    business_use=str(o.get("business_use", "")).strip() or str(o.get("what_it_represents", "")).strip(),
                    destination_format=str(o.get("destination_format", "")).strip(),
                )
                for o in data.get("outputs", [])
                if str(o.get("output_deliverable", "")).strip()
            ]

            # 5. Parse stages
            stages = [
                BusinessReportStageItem(
                    stage_number=int(s.get("stage_number", idx)),
                    stage_name=str(s.get("stage_name", "")).strip(),
                    description=str(s.get("description", "")).strip(),
                    operational_explanation=str(s.get("operational_explanation", "")).strip(),
                )
                for idx, s in enumerate(data.get("sequential_stages", []), start=1)
                if str(s.get("stage_name", "")).strip()
            ]

            # 6. Parse business rules
            rules = [
                BusinessReportRuleItem(
                    business_rule=str(r.get("business_rule", "")).strip(),
                    category=str(r.get("category", "")).strip(),
                    evidence_configuration=str(r.get("evidence_configuration", "")).strip(),
                )
                for r in data.get("business_rules", [])
                if str(r.get("business_rule", "")).strip()
            ]

            # 7. Parse lineage
            lineage = [
                BusinessReportLineageItem(
                    source_datasets=l.get("source_datasets", ""),
                    major_business_transformation=str(l.get("major_business_transformation", "")).strip(),
                    target_deliverable=str(l.get("target_deliverable", "")).strip(),
                )
                for l in data.get("lineage", [])
                if str(l.get("target_deliverable", "")).strip()
            ]

            return BusinessReportContent(
                workflow_title=str(data.get("workflow_title", "")).strip(),
                workflow_description=str(data.get("workflow_description", "")).strip(),
                executive_summary=exec_summary,
                methods_of_analysis=methods_analysis,
                findings=findings[:7],
                conclusions=conclusions,
                inputs=inputs,
                outputs=outputs,
                sequential_stages=stages,
                business_rules=rules,
                lineage=lineage,
            )
        except Exception as e:
            logger.warning("[LLM] Validation failed while parsing BusinessReportContent: %s", e)
            return None

    def generate_all_tool_summaries(
        self,
        workflow: Workflow,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> dict[int, NarrativeResult]:
        """Pre-generate summaries for all tools in a workflow."""
        results: dict[int, NarrativeResult] = {}
        for tool_id, tool in workflow.tools.items():
            results[tool_id] = self.generate_tool_summary(workflow, tool, graph, workflow_id=workflow_id)
        return results


_global_generator: LLMNarrativeGenerator | None = None


def get_default_generator() -> LLMNarrativeGenerator:
    """Access the global default narrative generator."""
    global _global_generator
    if _global_generator is None:
        _global_generator = LLMNarrativeGenerator()
    return _global_generator


def set_default_generator(generator: LLMNarrativeGenerator | None) -> None:
    """Override the default narrative generator (for tests)."""
    global _global_generator
    _global_generator = generator
