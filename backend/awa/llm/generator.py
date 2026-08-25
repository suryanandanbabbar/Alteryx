"""Deterministic facts extraction and narrative generation service with validation and fallback."""

from __future__ import annotations

import logging
import re
from typing import Any
import networkx as nx

from awa.model.workflow import Workflow
from awa.model.tool import Tool
from awa.model.business_summary import WorkflowBusinessSummary
from awa.tools.catalog import get_tool_summary
from awa.tools import humanize_tool_configuration

from .client import LLMClient, get_default_llm_client
from .schemas import NarrativeResult, ToolFacts, WorkflowFacts
from .prompts import (
    TOOL_PROMPT_VERSION,
    WORKFLOW_PURPOSE_PROMPT_VERSION,
    EXEC_SUMMARY_PROMPT_VERSION,
    TOOL_SYSTEM_PROMPT,
    WORKFLOW_PURPOSE_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    build_tool_user_prompt,
    build_workflow_purpose_user_prompt,
    build_executive_summary_user_prompt,
)
from .cache import LLMNarrativeCache, get_global_narrative_cache, compute_cache_key

logger = logging.getLogger("awa.llm")


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
        r"^description:\s*",
        r"^summary:\s*",
    ]
    for pattern in prefixes_to_strip:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

    return text


def extract_tool_facts(workflow: Workflow, tool: Tool, graph: nx.DiGraph | None = None) -> ToolFacts:
    """Extract deterministic facts for a single tool from the workflow model and DAG."""
    # Upstream and downstream tools
    upstreams: list[dict[str, Any]] = []
    downstreams: list[dict[str, Any]] = []

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
            for succ_id in graph.successors(tool.tool_id):
                succ_tool = workflow.tools.get(succ_id)
                if succ_tool:
                    downstreams.append({
                        "tool_id": succ_id,
                        "tool_type": succ_tool.tool_type,
                        "name": succ_tool.name or succ_tool.tool_type,
                        "annotation": succ_tool.annotation,
                    })

    # Humanized configuration
    raw_cfg = tool.configuration.parsed if tool.configuration else {}
    cleaned_cfg = humanize_tool_configuration(tool.tool_type, raw_cfg)

    # Technical fallback description from tool registry
    tech_function = get_tool_summary(tool.plugin or tool.tool_type)

    output_flds = [f.name for f in tool.output_fields if f.name]

    return ToolFacts(
        tool_id=tool.tool_id,
        tool_type=tool.tool_type,
        tool_name=tool.name or tool.tool_type,
        workflow_role=tool.container_name or "Processing",
        annotation=tool.annotation,
        configuration_summary=cleaned_cfg,
        upstream_tools=upstreams,
        downstream_tools=downstreams,
        container_name=tool.container_name,
        output_fields=output_flds,
        technical_function=tech_function,
    )


def extract_workflow_facts(workflow: Workflow, business_summary: WorkflowBusinessSummary) -> WorkflowFacts:
    """Extract deterministic workflow facts for business purpose and executive summary generation."""
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


class LLMNarrativeGenerator:
    """High-level orchestration service for narrative generation with caching and fallback.
    
    The generator:
    1. Extracts deterministic facts from the workflow model
    2. Checks the in-memory cache
    3. Calls the LLM client if cache miss
    4. Validates and sanitizes the response
    5. Falls back to deterministic tool registry summaries on failure
    6. Logs structured generation status (never secrets)
    """

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

    def generate_tool_summary(
        self,
        workflow: Workflow,
        tool: Tool,
        graph: nx.DiGraph | None = None,
        workflow_id: str = "",
    ) -> NarrativeResult:
        """Generate a workflow-specific 'What It Does' summary for a tool.
        
        Fallback uses the deterministic tool registry summary — never raw annotation.
        The annotation is input context for the LLM, not the fallback output.
        """
        # 1. Deterministic fallback: ALWAYS use tool registry, never raw annotation
        fallback_text = get_tool_summary(tool.plugin or tool.tool_type)

        # 2. Extract facts (annotation is included as LLM input, not fallback)
        facts = extract_tool_facts(workflow, tool, graph)
        wf_key = workflow_id or workflow.metadata.name or "default_workflow"
        cache_key = compute_cache_key(
            workflow_id=wf_key,
            scope_key=f"tool_{tool.tool_id}",
            prompt_version=TOOL_PROMPT_VERSION,
            model_name=self.client.model_name,
            facts_payload=facts.to_dict(),
        )

        # 3. Check cache
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # 4. Generate via LLM
        system_prompt = TOOL_SYSTEM_PROMPT
        user_prompt = build_tool_user_prompt(facts)
        raw_response = self.client.generate(system_prompt, user_prompt)
        cleaned = _clean_narrative_text(raw_response)

        # 5. Validate output
        if cleaned and len(cleaned.split()) >= 3 and len(cleaned) <= 500:
            result = NarrativeResult(
                text=cleaned,
                source="llm",
                model=self.client.model_name,
                prompt_version=TOOL_PROMPT_VERSION,
            )
            self._cache.set(cache_key, result)
            logger.debug(
                "LLM narrative generated: type=tool_summary tool_id=%d source=llm model=%s",
                tool.tool_id, self.client.model_name,
            )
            return result

        # 6. Fallback with logging
        logger.debug(
            "LLM narrative fallback: type=tool_summary tool_id=%d source=deterministic reason=%s",
            tool.tool_id,
            "empty_response" if not cleaned else "validation_failed",
        )
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

        # Check cache
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Generate via LLM
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
            logger.debug(
                "LLM narrative generated: type=business_purpose source=llm model=%s",
                self.client.model_name,
            )
            return result

        logger.debug(
            "LLM narrative fallback: type=business_purpose source=deterministic reason=%s",
            "empty_response" if not cleaned else "validation_failed",
        )
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

        # Check cache
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # Generate via LLM
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
            logger.debug(
                "LLM narrative generated: type=executive_summary source=llm model=%s",
                self.client.model_name,
            )
            return result

        logger.debug(
            "LLM narrative fallback: type=executive_summary source=deterministic reason=%s",
            "empty_response" if not cleaned else "validation_failed",
        )
        fallback_result = NarrativeResult(
            text=fallback_text,
            source="deterministic_fallback",
            model="deterministic",
            prompt_version=EXEC_SUMMARY_PROMPT_VERSION,
        )
        return fallback_result

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


# Global generator instance
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
