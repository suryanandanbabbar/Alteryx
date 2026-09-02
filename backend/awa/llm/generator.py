"""Deterministic facts extraction and narrative generation service with validation and fallback."""

from __future__ import annotations

import json
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

from awa.model.tool_specifications import format_input_tools, format_output_tools
from awa.model.sttm import STTMDocument, STTMMapping
from awa.analysis.sttm_extractor import extract_sttm, build_sttm_evidence_context
from awa.analysis.sttm_validator import STTMValidator

from .client import LLMClient, get_default_llm_client
from .schemas import (
    NarrativeResult,
    BusinessPurposeResult,
    ToolFacts,
    WorkflowFacts,
    BusinessReportContent,
    BusinessReportInputItem,
    BusinessReportOutputItem,
    BusinessReportStageItem,
    BusinessReportRuleItem,
    BusinessReportLineageItem,
    ComprehensiveWorkflowContext,
    ProcessStageContent,
    WorkflowProcessStages,
    STTMMappingItem,
    STTMLLMResponse,
)
from .prompts import (
    TOOL_PROMPT_VERSION,
    WORKFLOW_PURPOSE_PROMPT_VERSION,
    EXEC_SUMMARY_PROMPT_VERSION,
    METHODS_OF_ANALYSIS_PROMPT_VERSION,
    FINDINGS_PROMPT_VERSION,
    CONCLUSIONS_PROMPT_VERSION,
    BUSINESS_REPORT_PROMPT_VERSION,
    TOOL_SPECIFICATIONS_PROMPT_VERSION,
    PROCESS_STAGES_PROMPT_VERSION,
    STTM_PROMPT_VERSION,
    TOOL_SYSTEM_PROMPT,
    WORKFLOW_PURPOSE_SYSTEM_PROMPT,
    build_workflow_purpose_system_prompt,
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    METHODS_OF_ANALYSIS_SYSTEM_PROMPT,
    FINDINGS_SYSTEM_PROMPT,
    CONCLUSIONS_SYSTEM_PROMPT,
    BUSINESS_REPORT_SYSTEM_PROMPT,
    TOOL_SPECIFICATIONS_SYSTEM_PROMPT,
    PROCESS_STAGES_SYSTEM_PROMPT,
    STTM_SYSTEM_PROMPT,
    build_tool_user_prompt,
    build_workflow_purpose_user_prompt,
    build_executive_summary_user_prompt,
    build_methods_of_analysis_user_prompt,
    build_findings_user_prompt,
    build_methods_conclusions_user_prompt,
    build_business_report_user_prompt,
    build_tool_specifications_user_prompt,
    build_process_stages_user_prompt,
    build_sttm_user_prompt,
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
    business_summary: WorkflowBusinessSummary | None = None,
    graph: nx.DiGraph | None = None,
) -> ComprehensiveWorkflowContext:
    """Extract rich, authoritative workflow context from CIR, tools, formulas, and graph topology."""
    if isinstance(business_summary, nx.DiGraph) and graph is None:
        graph = business_summary
        business_summary = None

    if business_summary is None:
        from awa.analysis.business_intelligence import generate_business_summary
        from awa.graph.builder import execution_order
        g = graph or nx.DiGraph()
        try:
            steps = execution_order(g)
            e_order = [s.tool_id for s in steps if s.tool_id in workflow.tools]
        except Exception:
            e_order = list(workflow.tools.keys())
        business_summary = generate_business_summary(workflow, g, e_order)

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


DISALLOWED_PURPOSE_INDICATORS: tuple[str, ...] = (
    "to determine the primary",
    "let's analyze",
    "let us analyze",
    "step by step",
    "tier 1",
    "tier 2",
    "tier 3",
    "tier 4",
    "tier 5",
    "tier 6",
    "tier 7",
    "evidence hierarchy",
    "classification hierarchy",
    "classification debate",
    "classification reasoning",
    "given these observations",
    "given observations",
    "according to the classification",
    "rejected business area",
    "rejected areas",
    "rejected because",
    "facts provided:",
    "based on the facts provided",
    "classification evidence",
    "prompt instructions",
    "internal reasoning",
    "chain of thought",
    "we classify",
    "we categorize",
    "final classification",
    "primary business function:",
    "business area tag:",
    "classification:",
    "reasoning:",
    "evidence:",
    "observations:",
    "justification:",
    "in conclusion",
    "prompt response",
    "```json",
    "```",
)


def _is_clean_business_purpose(text: str | None) -> bool:
    """Validate that text is a concise, polished business purpose and not LLM reasoning, analysis, or prompt text."""
    if not text or not isinstance(text, str):
        return False

    cleaned = text.strip()
    if not cleaned:
        return False

    # Disallow raw JSON, arrays, code blocks, markdown headers, or multi-paragraph formatting
    if cleaned.startswith("{") or cleaned.startswith("[") or cleaned.endswith("}") or cleaned.endswith("]"):
        return False
    if "```" in cleaned:
        return False
    if "\n\n" in cleaned or "\n#" in cleaned or "\n- " in cleaned or "\n1. " in cleaned:
        return False

    # Word count: strictly one polished paragraph ~40-75 words; reject verbose reasoning dumps (> 110 words)
    words = cleaned.split()
    if len(words) < 5 or len(words) > 110:
        return False

    lower_text = cleaned.lower()
    for indicator in DISALLOWED_PURPOSE_INDICATORS:
        if indicator in lower_text:
            return False

    # Disallow conversational lead-ins
    disallowed_starts = (
        "here is", "this json", "based on", "the workflow is classified",
        "according to", "in this analysis", "i have analyzed", "as an ai",
        "we classify", "we determine",
    )
    for start in disallowed_starts:
        if lower_text.startswith(start):
            return False

    return True


def _extract_structured_purpose_payload(raw_response: str | None) -> dict[str, Any] | None:
    """Extract structured JSON payload containing business_purpose, business_function, and business_area_tag.

    Extracts valid JSON even when the model wraps it in markdown code blocks or includes
    conversational preamble / thinking before or after the JSON.
    """
    if not raw_response or not isinstance(raw_response, str):
        return None

    text = raw_response.strip()
    if not text:
        return None

    # 1. Direct parse if response is clean JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "business_purpose" in parsed:
            return parsed
    except Exception:
        pass

    # 2. Extract from markdown code blocks (e.g. ```json ... ```)
    code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    for block in code_blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, dict) and "business_purpose" in parsed:
                return parsed
        except Exception:
            pass

    # 3. Progressive JSON scanning for any object containing "business_purpose"
    decoder = json.JSONDecoder()
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, idx=start)
            if isinstance(obj, dict) and "business_purpose" in obj:
                return obj
            pos = end
        except Exception:
            pos = start + 1

    return None


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
        output_evidence: list[dict[str, Any]] | None = None,
        input_sources: list[str] | None = None,
    ) -> BusinessPurposeResult:
        """Generate a canonical workflow-level Business Purpose description, Function, and normalized Business Area Tag.

        Authoritative single owner of:
        - Structured Business Purpose, Function & Area Tag prompt orchestration
        - Deterministic validation against configured ALLOWED_BUSINESS_AREAS vocabulary
        - Strict validation that business_purpose contains only concise business description
        - Semantic coherence & conflict resolution between function and tag
        - Guaranteed fallback to deterministic 7-tier classification on failure/unavailability
        """
        from awa.analysis.business_area_classifier import (
            ALLOWED_BUSINESS_AREAS,
            classify_business_area_deterministic,
            classify_business_function_deterministic,
            BUSINESS_AREA_DESCRIPTIONS,
            BUSINESS_AREA_TAXONOMY_VERSION,
        )

        wf_name = (
            (workflow.metadata.name if (workflow and workflow.metadata and workflow.metadata.name) else "")
            or (workflow_id if (workflow_id and not workflow_id.startswith("wf_") and not workflow_id.startswith("analysis_")) else "")
        )

        # Build complete input sources if not explicitly supplied
        if input_sources is None:
            resolved_sources: list[str] = []
            if business_summary and business_summary.source_inputs:
                for inp in business_summary.source_inputs:
                    val = inp.source_filename or inp.name or inp.raw_source
                    if val and val.lower() not in ("in-memory configuration", "standard input stream"):
                        resolved_sources.append(val)
            if workflow and workflow.tools:
                for tid, tool in workflow.tools.items():
                    if tool.tool_type in ("DbFileInput", "FileInput", "TextInput", "Directory", "DynamicInput"):
                        cfg = tool.configuration.parsed if (tool.configuration and hasattr(tool.configuration, "parsed") and isinstance(tool.configuration.parsed, dict)) else (tool.configuration if isinstance(tool.configuration, dict) else {})
                        fp = cfg.get("file_path") or cfg.get("File") or cfg.get("source_file") or cfg.get("table_name")
                        if fp and str(fp) not in resolved_sources:
                            resolved_sources.append(str(fp))
            input_sources = resolved_sources

        existing_func = getattr(business_summary, "business_function", "") or ""

        det_class = classify_business_area_deterministic(
            output_evidence or [],
            business_purpose=business_summary.business_purpose or "",
            workflow_name=wf_name,
            business_function=existing_func,
            input_sources=input_sources or [],
        )
        fallback_tag = "Other / Unclassified" if det_class.business_area in ("UNCLASSIFIED", "Other / Unclassified") else det_class.business_area
        fallback_func = existing_func or classify_business_function_deterministic(
            fallback_tag,
            workflow_name=wf_name,
            business_purpose=business_summary.business_purpose or "",
        )

        # Ensure fallback_purpose is strictly clean and concise
        if business_summary.business_purpose and _is_clean_business_purpose(business_summary.business_purpose):
            fallback_purpose = business_summary.business_purpose
        else:
            fallback_purpose = (
                f"Automates {fallback_func.lower()} for {wf_name or 'the workflow'}, "
                f"processing operational data to generate business deliverables and decision outputs."
            )

        # Guard: If LLM client is unavailable or not configured, return deterministic fallback directly
        if not self.client or not getattr(self.client, "is_available", True):
            return BusinessPurposeResult(
                business_purpose=fallback_purpose,
                business_function=fallback_func,
                business_area_tag=fallback_tag,
                source="deterministic_fallback",
                business_area_taxonomy_version=BUSINESS_AREA_TAXONOMY_VERSION,
                classification_conflict=False,
                classification_evidence=det_class.evidence,
                model="deterministic",
                prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
            )

        facts = extract_workflow_facts(workflow, business_summary)
        wf_key = workflow_id or wf_name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="business_purpose",
            prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, BusinessPurposeResult):
            # Double-check cached business_purpose is clean; if stale/dirty, invalidate cache
            if _is_clean_business_purpose(cached.business_purpose):
                logger.info("[LLM CACHE] type=business_purpose status=HIT")
                return cached
            logger.info("[LLM CACHE] type=business_purpose status=DIRTY_INVALIDATED")

        logger.info("[LLM CACHE] type=business_purpose status=MISS")

        system_prompt = build_workflow_purpose_system_prompt(BUSINESS_AREA_DESCRIPTIONS)
        user_prompt = build_workflow_purpose_user_prompt(facts)

        try:
            raw_response = self.client.generate(system_prompt, user_prompt)
            parsed = _extract_structured_purpose_payload(raw_response)

            if isinstance(parsed, dict):
                llm_purpose = str(parsed.get("business_purpose", "")).strip()
                llm_func = str(parsed.get("business_function", "")).strip()
                llm_tag = str(parsed.get("business_area_tag", "")).strip()

                # Clean wrapping quotes if any
                if (llm_purpose.startswith('"') and llm_purpose.endswith('"')) or (
                    llm_purpose.startswith("'") and llm_purpose.endswith("'")
                ):
                    llm_purpose = llm_purpose[1:-1].strip()

                valid_areas = set(ALLOWED_BUSINESS_AREAS) | {"Other / Unclassified", "UNCLASSIFIED"}

                # Strictly validate that business_purpose is clean/concise and business_area_tag is allowed
                if _is_clean_business_purpose(llm_purpose) and llm_tag in valid_areas:
                    # Ingest or infer business_function
                    if not llm_func:
                        llm_func = classify_business_function_deterministic(
                            llm_tag, workflow_name=wf_name, business_purpose=llm_purpose
                        )

                    # Semantic Coherence & Conflict Guard:
                    # Check whether Tier 1 (workflow name) or Tier 2 (business function)
                    # strictly contradicts the LLM's selected tag (e.g. data-domain distraction).
                    conflict = False
                    conflict_evidence: list[str] = []
                    det_check = classify_business_area_deterministic(
                        output_evidence or [],
                        business_purpose=llm_purpose,
                        workflow_name=wf_name,
                        business_function=llm_func,
                        input_sources=input_sources or [],
                    )
                    strong_functional_domain = det_check.business_area

                    if (
                        strong_functional_domain in ALLOWED_BUSINESS_AREAS
                        and strong_functional_domain != "UNCLASSIFIED"
                        and llm_tag != strong_functional_domain
                        and any("Tier 1" in e or "Tier 2" in e for e in det_check.evidence)
                    ):
                        logger.warning(
                            "[LLM CONFLICT GUARD] Detected functional contradiction: LLM returned tag='%s' "
                            "but strong functional evidence indicates '%s' (function='%s'). Overriding to functional tag.",
                            llm_tag,
                            strong_functional_domain,
                            llm_func,
                        )
                        conflict = True
                        normalized_tag = strong_functional_domain
                        conflict_evidence = [
                            f"Conflict override: Tier 1/2 functional evidence ('{llm_func}') overrides LLM tag '{llm_tag}'"
                        ] + det_check.evidence
                    else:
                        normalized_tag = "Other / Unclassified" if llm_tag == "UNCLASSIFIED" else llm_tag
                        conflict_evidence = [f"LLM classified as {normalized_tag}"]

                    result = BusinessPurposeResult(
                        business_purpose=llm_purpose,
                        business_function=llm_func,
                        business_area_tag=normalized_tag,
                        source="llm",
                        business_area_taxonomy_version=BUSINESS_AREA_TAXONOMY_VERSION,
                        classification_conflict=conflict,
                        classification_evidence=conflict_evidence,
                        model=self.client.model_name,
                        prompt_version=WORKFLOW_PURPOSE_PROMPT_VERSION,
                    )
                    self._cache.set(cache_key, result)
                    logger.info(
                        "[LLM] business_purpose accepted: tag='%s', func='%s', words=%d, conflict=%s",
                        normalized_tag,
                        llm_func,
                        len(llm_purpose.split()),
                        conflict,
                    )
                    return result
                else:
                    logger.warning(
                        "[LLM] Structured output rejected (valid_purpose=%s, valid_tag=%s). Using deterministic fallback.",
                        _is_clean_business_purpose(llm_purpose),
                        llm_tag in valid_areas,
                    )
            else:
                logger.warning("[LLM] Output did not contain valid structured JSON. Using deterministic fallback.")
        except Exception as exc:
            logger.warning("[LLM] generate_business_purpose failed: %s. Using deterministic fallback.", exc)

        fallback_result = BusinessPurposeResult(
            business_purpose=fallback_purpose,
            business_function=fallback_func,
            business_area_tag=fallback_tag,
            source="deterministic_fallback",
            business_area_taxonomy_version=BUSINESS_AREA_TAXONOMY_VERSION,
            classification_conflict=False,
            classification_evidence=det_class.evidence,
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

            # Reject empty or trivial core analytical sections
            if not exec_summary or len(exec_summary) < 40:
                logger.warning("[LLM] Validation failed: executive_summary is too short (< 40 chars) or empty")
                return None
            if not methods_analysis or len(methods_analysis) < 30:
                logger.warning("[LLM] Validation failed: methods_of_analysis is too short (< 30 chars) or empty")
                return None
            if not conclusions or len(conclusions) < 20:
                logger.warning("[LLM] Validation failed: conclusions is too short (< 20 chars) or empty")
                return None

            # Check for prohibited generic AI filler in executive summary & conclusions
            prohibited_cliches = [
                "valuable insights",
                "meaningful insights",
                "enhances decision-making",
                "streamlines business processes",
                "streamlines data processing",
                "improves efficiency",
                "supports data-driven decisions",
                "ensures robust analysis",
                "facilitates informed decisions",
                "produces useful outputs",
            ]
            all_text_lower = f"{exec_summary} {methods_analysis} {conclusions}".lower()
            for cliche in prohibited_cliches:
                if cliche in all_text_lower:
                    logger.warning("[LLM] Validation warning: found generic AI cliché '%s' in report narrative", cliche)

            # Check that recommendations/action directives are NOT present in executive summary
            forbidden_phrases = ["we recommend", "the business should", "recommended action", "recommendation:"]
            for fp in forbidden_phrases:
                if fp in all_text_lower:
                    logger.warning("[LLM] Validation failed: found forbidden recommendation phrasing '%s'", fp)
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

    def generate_tool_specification(
        self,
        workflow: Workflow,
        tool: Tool,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> dict[str, str]:
        """Generate workflow-specific Role and Data Flow Explanation for a tool."""
        inp_str = format_input_tools(workflow, graph, tool.tool_id)
        out_str = format_output_tools(workflow, graph, tool.tool_id)
        ttype = tool.tool_type or "Tool"

        fallback_role = f"Applies the configured {ttype} operation to the incoming data stream."
        if inp_str == "Source" and out_str == "None":
            fallback_data_flow = "Ingests source records and performs localized processing."
        elif inp_str == "Source":
            fallback_data_flow = f"Ingests source records and passes the data stream to {out_str}."
        elif out_str == "None":
            fallback_data_flow = f"Receives processed data from {inp_str} and writes to the final output destination."
        else:
            fallback_data_flow = f"Receives data from {inp_str} and passes the resulting stream to {out_str}."

        facts = extract_tool_facts(workflow, tool, graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key=f"tool_spec_{tool.tool_id}",
            prompt_version=TOOL_SPECIFICATIONS_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=tool_spec tool_id=%d status=HIT", tool.tool_id)
            try:
                import json
                cached_data = json.loads(cached.text)
                return {
                    "role": cached_data.get("role", fallback_role),
                    "data_flow_explanation": cached_data.get("data_flow_explanation", fallback_data_flow),
                }
            except Exception:
                pass

        logger.info("[LLM CACHE] type=tool_spec tool_id=%d status=MISS", tool.tool_id)

        system_prompt = TOOL_SPECIFICATIONS_SYSTEM_PROMPT
        user_prompt = build_tool_specifications_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=400)

        parsed_role = ""
        parsed_data_flow = ""
        try:
            import json
            clean_json = raw_response.strip()
            if "```" in clean_json:
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.MULTILINE)
                clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE)
            start = clean_json.find("{")
            end = clean_json.rfind("}")
            if start != -1 and end != -1:
                clean_json = clean_json[start : end + 1]
                data = json.loads(clean_json)
                parsed_role = str(data.get("role", "")).strip()
                parsed_data_flow = str(data.get("data_flow_explanation", "")).strip()
        except Exception as e:
            logger.warning("[LLM] Failed to parse tool spec JSON for tool #%d: %s", tool.tool_id, e)

        role_final = parsed_role if (parsed_role and len(parsed_role) >= 15) else fallback_role
        data_flow_final = parsed_data_flow if (parsed_data_flow and len(parsed_data_flow) >= 15) else fallback_data_flow

        import json
        result = NarrativeResult(
            text=json.dumps({"role": role_final, "data_flow_explanation": data_flow_final}),
            source="llm" if (parsed_role and parsed_data_flow) else "deterministic_fallback",
            model=self.client.model_name,
            prompt_version=TOOL_SPECIFICATIONS_PROMPT_VERSION,
        )
        self._cache.set(cache_key, result)

        return {
            "role": role_final,
            "data_flow_explanation": data_flow_final,
        }

    def generate_all_tool_specifications(
        self,
        workflow: Workflow,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> dict[int, dict[str, str]]:
        """Generate tool specifications for all tools in a workflow."""
        results: dict[int, dict[str, str]] = {}
        for tool_id, tool in workflow.tools.items():
            results[tool_id] = self.generate_tool_specification(workflow, tool, graph, workflow_id=workflow_id)
        return results

    def generate_process_stages(
        self,
        workflow: Workflow,
        graph: nx.DiGraph | None = None,
        business_summary: WorkflowBusinessSummary | None = None,
        workflow_id: str = "",
    ) -> list[BusinessStage]:
        """Generate structured business process stages for the Overview page."""
        from awa.model.business_summary import BusinessStage

        context = extract_comprehensive_workflow_context(workflow, business_summary=business_summary, graph=graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="process_stages",
            prompt_version=PROCESS_STAGES_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=context.to_dict(),
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=process_stages status=HIT")
            stages = self._parse_process_stages_json(cached.text, workflow, graph)
            if stages:
                return stages

        logger.info("[LLM CACHE] type=process_stages status=MISS")

        system_prompt = PROCESS_STAGES_SYSTEM_PROMPT
        user_prompt = build_process_stages_user_prompt(context.to_dict())
        raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=1500)

        stages = self._parse_process_stages_json(raw_response, workflow, graph)
        if not stages:
            logger.warning("[LLM] Process stages generation failed validation, using generic deterministic fallback.")
            stages = self._generate_fallback_process_stages(workflow, graph, business_summary)
            import json
            fallback_payload = {
                "stages": [
                    {
                        "stage_number": s.stage_number,
                        "stage_name": s.name,
                        "category": s.short_title.split()[-1] if s.short_title else "PROCESS",
                        "description": s.description,
                        "purpose": s.business_purpose,
                        "transformation": s.major_transformation,
                        "key_actions": s.annotations,
                        "tool_ids": s.tool_ids,
                    }
                    for s in stages
                ]
            }
            res = NarrativeResult(
                text=json.dumps(fallback_payload),
                source="deterministic_fallback",
                model=self.client.model_name,
                prompt_version=PROCESS_STAGES_PROMPT_VERSION,
            )
            self._cache.set(cache_key, res)
            return stages

        import json
        cache_payload = {
            "stages": [
                {
                    "stage_number": s.stage_number,
                    "stage_name": s.name,
                    "category": s.short_title.split()[-1] if s.short_title else "PROCESS",
                    "description": s.description,
                    "purpose": s.business_purpose,
                    "transformation": s.major_transformation,
                    "key_actions": s.annotations,
                    "tool_ids": s.tool_ids,
                }
                for s in stages
            ]
        }
        res = NarrativeResult(
            text=json.dumps(cache_payload),
            source="llm",
            model=self.client.model_name,
            prompt_version=PROCESS_STAGES_PROMPT_VERSION,
        )
        self._cache.set(cache_key, res)

        return stages

    def _parse_process_stages_json(
        self,
        raw_json: str,
        workflow: Workflow,
        graph: nx.DiGraph | None = None,
    ) -> list[BusinessStage] | None:
        """Parse, validate, and enforce 100% tool coverage for LLM process stages."""
        from awa.model.business_summary import BusinessStage
        try:
            import json
            clean_json = raw_json.strip()
            if "```" in clean_json:
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.MULTILINE)
                clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE)
            start = clean_json.find("{")
            end = clean_json.rfind("}")
            if start == -1 or end == -1:
                return None
            clean_json = clean_json[start : end + 1]
            data = json.loads(clean_json)
            raw_stages = data.get("stages") or data.get("sequential_stages", [])
            if not isinstance(raw_stages, list) or not raw_stages:
                return None

            all_wf_tool_ids = set(workflow.tools.keys())
            assigned_tool_ids: set[int] = set()
            parsed_stages: list[BusinessStage] = []

            for idx, item in enumerate(raw_stages, start=1):
                if not isinstance(item, dict):
                    continue
                s_name = str(item.get("stage_name", "")).strip()
                if not s_name:
                    continue
                s_cat = str(item.get("category", "")).strip().upper() or "PROCESS"
                s_cat = re.sub(r"[^A-Z0-9_ -]", " ", s_cat).strip()
                s_cat = " ".join(s_cat.split())[:35] or "PROCESS"
                s_desc = str(item.get("description", "")).strip()
                s_purpose = str(item.get("purpose", "")).strip() or s_desc
                s_trans = str(item.get("transformation") or item.get("operational_explanation", "")).strip()
                s_actions = [str(a).strip() for a in item.get("key_actions", []) if str(a).strip()]

                raw_tids = item.get("tool_ids", [])
                valid_tids: list[int] = []
                for tid_val in raw_tids:
                    try:
                        tid_int = int(str(tid_val).replace("#", "").strip())
                        if tid_int in all_wf_tool_ids and tid_int not in assigned_tool_ids:
                            valid_tids.append(tid_int)
                            assigned_tool_ids.add(tid_int)
                    except (ValueError, TypeError):
                        pass

                stage_num = int(item.get("stage_number", idx))
                short_title = f"{stage_num:02d} {s_cat}"

                stage_obj = BusinessStage(
                    stage_number=stage_num,
                    name=s_name,
                    short_title=short_title,
                    summary=s_desc,
                    description=s_desc,
                    business_purpose=s_purpose,
                    major_transformation=s_trans,
                    tool_ids=valid_tids,
                    tool_count=len(valid_tids),
                    annotations=s_actions,
                    transformations=[s_trans] if s_trans else [],
                )
                parsed_stages.append(stage_obj)

            if not parsed_stages:
                return None

            # Tool Coverage Guarantee: ensure every workflow tool is assigned to a stage
            unassigned_tids = all_wf_tool_ids - assigned_tool_ids
            if unassigned_tids:
                for tid in sorted(unassigned_tids):
                    assigned = False
                    if graph is not None:
                        preds = set(graph.predecessors(tid)) if graph.has_node(tid) else set()
                        succs = set(graph.successors(tid)) if graph.has_node(tid) else set()
                        for stg in parsed_stages:
                            if set(stg.tool_ids) & (preds | succs):
                                stg.tool_ids.append(tid)
                                stg.tool_count = len(stg.tool_ids)
                                assigned = True
                                break
                    if not assigned:
                        closest_stage = min(
                            parsed_stages,
                            key=lambda stg: min([abs(tid - t) for t in stg.tool_ids] or [999]),
                        )
                        closest_stage.tool_ids.append(tid)
                        closest_stage.tool_count = len(closest_stage.tool_ids)

            # Sort tool_ids inside each stage
            for stg in parsed_stages:
                stg.tool_ids.sort()
                stg.tool_count = len(stg.tool_ids)

            return parsed_stages
        except Exception as e:
            logger.warning("[LLM] Error parsing process stages JSON: %s", e)
            return None

    def _generate_fallback_process_stages(
        self,
        workflow: Workflow,
        graph: nx.DiGraph | None,
        business_summary: WorkflowBusinessSummary | None,
    ) -> list[BusinessStage]:
        """Derive generic factual process stages based on graph topology and container structures."""
        from awa.model.business_summary import BusinessStage
        from awa.graph.builder import execution_order

        ordered_tids: list[int] = []
        if graph is not None:
            try:
                exec_steps = execution_order(graph)
                ordered_tids = [s.tool_id for s in exec_steps if s.tool_id in workflow.tools]
            except Exception:
                ordered_tids = sorted(list(workflow.tools.keys()))
        else:
            ordered_tids = sorted(list(workflow.tools.keys()))

        # If workflow has containers, group by containers
        if workflow.containers:
            container_tools: dict[int, list[int]] = {}
            container_order: list[int] = []
            for tid in ordered_tids:
                tool = workflow.tools.get(tid)
                if not tool:
                    continue
                cid = tool.container_id or 0
                if cid not in container_tools:
                    container_tools[cid] = []
                    container_order.append(cid)
                container_tools[cid].append(tid)

            stages: list[BusinessStage] = []
            stage_num = 1
            for cid in container_order:
                t_ids = container_tools[cid]
                if not t_ids:
                    continue
                cont = workflow.containers.get(cid)
                caption = cont.caption.strip() if cont and cont.caption else f"Processing Phase {stage_num:02d}"
                clean_cat = re.sub(r"[^a-zA-Z0-9\s]", " ", caption).strip().upper()
                cat_words = clean_cat.split()
                category = " ".join(cat_words[:4]) if cat_words else f"STAGE {stage_num:02d}"
                short_title = f"{stage_num:02d} {category}"

                tools_in_stage = [workflow.tools[t] for t in t_ids if t in workflow.tools]
                tool_types = list(dict.fromkeys(t.tool_type for t in tools_in_stage))
                types_str = ", ".join(tool_types[:3]) if tool_types else "processing"

                actions = [
                    workflow.tools[t].annotation.strip()
                    for t in t_ids
                    if workflow.tools.get(t) and workflow.tools[t].annotation and len(workflow.tools[t].annotation.strip()) > 3
                ]

                stages.append(
                    BusinessStage(
                        stage_number=stage_num,
                        name=caption,
                        short_title=short_title,
                        summary=f"Executes {caption.lower()} operations ({types_str})",
                        description=f"Executes {caption.lower()} operations ({types_str})",
                        business_purpose=f"Processes records through {len(t_ids)} workflow step{'s' if len(t_ids) != 1 else ''} ({types_str}).",
                        major_transformation=f"Applies {types_str} operations across {len(t_ids)} step{'s' if len(t_ids) != 1 else ''}.",
                        tool_ids=t_ids,
                        tool_count=len(t_ids),
                        annotations=actions[:4],
                        transformations=[f"{types_str} operations"],
                    )
                )
                stage_num += 1
            return stages

        # Dynamic operation clusters for workflows without containers
        group_specs = [
            (
                "DATA INGESTION",
                "Source Ingestion & Extraction",
                ("DbFileInput", "InputData", "TextInput", "DynamicInput", "Directory", "DateTimeNow"),
                "Ingests source records from input datasets into the workflow.",
                "Reads and validates raw input files for downstream processing.",
            ),
            (
                "DATA PREPARATION",
                "Data Cleansing & Filtering",
                ("Filter", "Select", "AlteryxSelect", "AutoField", "DateTime", "Sample", "Unique"),
                "Applies field selection, cleansing, and active record filtering.",
                "Filters unneeded records and standardizes schemas.",
            ),
            (
                "BUSINESS CALCULATIONS",
                "Calculations & Business Derivations",
                ("Formula", "MultiFieldFormula", "MultiRowFormula", "GenerateRows"),
                "Computes derived business metrics and evaluates rule expressions.",
                "Applies domain logic, formula rules, and calculated fields.",
            ),
            (
                "DATA ENRICHMENT",
                "Relational Enrichment & Joins",
                ("Join", "JoinMultiple", "FindReplace", "Union", "AppendFields", "FuzzyMatch"),
                "Integrates cross-dataset attributes using relational joins.",
                "Combines disparate streams into enriched analytical records.",
            ),
            (
                "METRIC AGGREGATION",
                "Analytical Summarization & Aggregation",
                ("Summarize", "CrossTab", "Transpose", "RunningTotal", "CountRecords"),
                "Aggregates metrics and pivots data for summary reporting.",
                "Computes group summary totals and structural pivots.",
            ),
            (
                "DATA ORDERING",
                "Sorting & Sequence Ordering",
                ("Sort", "RecordID", "Tile"),
                "Sorts records and assigns sequence order identifiers.",
                "Organizes data ordering for downstream delivery.",
            ),
            (
                "REPORT PUBLICATION",
                "Reporting Deliverables & Publication",
                ("DbFileOutput", "OutputData", "Render", "BrowseV2"),
                "Exports finalized analytical deliverables.",
                "Publishes processed datasets for business reporting.",
            ),
        ]

        assigned: set[int] = set()
        stages: list[BusinessStage] = []
        stage_num = 1
        for cat_tag, stage_title, matching_types, default_desc, default_purpose in group_specs:
            t_ids = [tid for tid in ordered_tids if tid in workflow.tools and workflow.tools[tid].tool_type in matching_types and tid not in assigned]
            if not t_ids:
                continue
            assigned.update(t_ids)

            tool_types_in_group = list(dict.fromkeys(
                workflow.tools[t].tool_type for t in t_ids if t in workflow.tools
            ))
            types_str = ", ".join(tool_types_in_group[:4])
            annotations = [workflow.tools[t].annotation.strip() for t in t_ids if workflow.tools.get(t) and workflow.tools[t].annotation and len(workflow.tools[t].annotation.strip()) > 3]
            specific_name = stage_title
            if len(t_ids) == 1 and annotations:
                specific_name = annotations[0]

            short_title = f"{stage_num:02d} {cat_tag}"
            summary = f"{default_desc} ({types_str})"
            purpose = f"{default_purpose} ({len(t_ids)} step{'s' if len(t_ids) != 1 else ''})"
            major_trans = f"Applies {types_str} operations across {len(t_ids)} step{'s' if len(t_ids) != 1 else ''}."

            stages.append(
                BusinessStage(
                    stage_number=stage_num,
                    name=specific_name,
                    short_title=short_title,
                    summary=summary,
                    description=summary,
                    business_purpose=purpose,
                    major_transformation=major_trans,
                    tool_ids=t_ids,
                    tool_count=len(t_ids),
                    annotations=annotations[:4],
                    transformations=[f"{workflow.tools[t].tool_type}: {workflow.tools[t].annotation or 'Processes data'}" for t in t_ids if workflow.tools.get(t)],
                )
            )
            stage_num += 1

        remaining = [tid for tid in ordered_tids if tid in workflow.tools and tid not in assigned]
        if remaining:
            if stages:
                stages[-1].tool_ids.extend(remaining)
                stages[-1].tool_ids.sort()
                stages[-1].tool_count = len(stages[-1].tool_ids)
            else:
                stages.append(
                    BusinessStage(
                        stage_number=1,
                        name="Workflow Data Processing",
                        short_title="01 DATA PROCESSING",
                        summary="Executes workflow data transformations.",
                        description="Executes workflow data transformations.",
                        business_purpose="Processes workflow records.",
                        major_transformation="Applies ETL operations.",
                        tool_ids=remaining,
                        tool_count=len(remaining),
                    )
                )

        return stages

    def generate_sttm(
        self,
        workflow: Workflow,
        graph: nx.DiGraph | None = None,
        business_summary: WorkflowBusinessSummary | None = None,
        workflow_id: str = "",
    ) -> STTMDocument:
        """Generate structured, validated Source-to-Target Mapping (STTM).
        
        Enforces Mapping Authority Invariant:
        1. Builds comprehensive deterministic evidence context from canonical workflow & DAG.
        2. Checks LLM cache.
        3. If client unavailable or disabled -> immediate deterministic fallback.
        4. Calls LLM with STTM_SYSTEM_PROMPT and build_sttm_user_prompt.
        5. Validates mappings via STTMValidator (checks source/target datasets, fields, DAG reachability, wildcards).
        6. Reconciles with deterministic baseline for 100% target completeness.
        7. Falls back to deterministic extraction if LLM times out, fails, or produces invalid output.
        """
        if graph is None:
            from awa.graph.builder import build_graph
            graph = build_graph(workflow)

        # 1. Deterministic evidence context & baseline
        evidence_context = build_sttm_evidence_context(workflow, graph, business_summary)
        deterministic_baseline: STTMDocument = evidence_context["deterministic_baseline"]

        # If LLM client is unavailable or disabled, immediately return deterministic baseline
        if not self.client.is_available:
            logger.info("[LLM STTM] Client unavailable or disabled — using deterministic baseline.")
            return deterministic_baseline

        validator = STTMValidator(evidence_context, graph)

        # 2. Check Cache
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key_payload = {
            "source_datasets": evidence_context.get("source_datasets", []),
            "target_deliverables": evidence_context.get("target_deliverables", []),
            "candidate_mappings": evidence_context.get("candidate_mappings", []),
        }
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key="sttm_mappings",
            prompt_version=STTM_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=cache_key_payload,
        )

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("[LLM CACHE] type=sttm_mappings status=HIT")
            llm_items = self._parse_sttm_json(cached.text)
            if llm_items is not None:
                return validator.reconcile_and_build_document(llm_items, workflow.metadata.name or "Workflow")

        logger.info("[LLM CACHE] type=sttm_mappings status=MISS")

        # 3. Call LLM
        system_prompt = STTM_SYSTEM_PROMPT
        user_prompt = build_sttm_user_prompt(evidence_context)
        try:
            raw_response = self.client.generate(system_prompt, user_prompt, max_tokens=2500)
        except Exception as e:
            logger.warning("[LLM STTM] Client exception: %s — falling back to deterministic baseline.", e)
            return deterministic_baseline

        llm_items = self._parse_sttm_json(raw_response)
        if llm_items is None:
            logger.warning("[LLM STTM] Generation failed or malformed JSON — falling back to deterministic baseline.")
            return deterministic_baseline

        # 4. Validate & Reconcile
        sttm_doc = validator.reconcile_and_build_document(llm_items, workflow.metadata.name or "Workflow")

        # 5. Store in cache on success
        import json
        self._cache.set(
            cache_key,
            NarrativeResult(
                text=json.dumps({"workflow_name": sttm_doc.workflow_name, "mappings": [m.to_dict() for m in sttm_doc.mappings]}),
                source="llm",
                model=self.client.model_name,
                prompt_version=STTM_PROMPT_VERSION,
            ),
        )

        return sttm_doc

    def _parse_sttm_json(self, raw_text: str | None) -> list[dict[str, Any]] | None:
        """Clean and parse LLM response into mapping item dictionaries."""
        if not raw_text or not raw_text.strip():
            return None

        clean = raw_text.strip()
        # Strip markdown code fences if present
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
            clean = clean.strip()

        try:
            import json
            data = json.loads(clean)
            if isinstance(data, dict):
                mappings = data.get("mappings")
                if isinstance(mappings, list):
                    return [m for m in mappings if isinstance(m, dict)]
            elif isinstance(data, list):
                return [m for m in data if isinstance(m, dict)]
        except Exception as e:
            logger.warning("[LLM STTM] Failed to parse JSON response: %s", e)

        return None



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
