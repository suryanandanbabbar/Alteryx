"""AWA LLM integration module for controlled narrative generation."""

from .config import LLMConfig, initialize_llm
from .client import LLMClient, AzureLlamaClient, FakeLLMClient, get_default_llm_client, set_default_llm_client
from .schemas import NarrativeResult, BusinessPurposeResult, ToolFacts, WorkflowFacts
from .prompts import TOOL_PROMPT_VERSION, WORKFLOW_PURPOSE_PROMPT_VERSION, EXEC_SUMMARY_PROMPT_VERSION
from .cache import LLMNarrativeCache, get_global_narrative_cache, compute_cache_key
from .generator import (
    LLMNarrativeGenerator,
    get_default_generator,
    set_default_generator,
    extract_tool_facts,
    extract_workflow_facts,
)

__all__ = [
    "LLMConfig",
    "initialize_llm",
    "LLMClient",
    "AzureLlamaClient",
    "FakeLLMClient",
    "get_default_llm_client",
    "set_default_llm_client",
    "NarrativeResult",
    "BusinessPurposeResult",
    "ToolFacts",
    "WorkflowFacts",
    "TOOL_PROMPT_VERSION",
    "WORKFLOW_PURPOSE_PROMPT_VERSION",
    "EXEC_SUMMARY_PROMPT_VERSION",
    "LLMNarrativeCache",
    "get_global_narrative_cache",
    "compute_cache_key",
    "LLMNarrativeGenerator",
    "get_default_generator",
    "set_default_generator",
    "extract_tool_facts",
    "extract_workflow_facts",
]
