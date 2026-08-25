"""Unit and integration tests for AWA LLM narrative generation layer."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import pytest

from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.field import Field
from awa.model.business_summary import (
    WorkflowBusinessSummary,
    BusinessInput,
    BusinessOutput,
    BusinessStage,
    BusinessTransformation,
    BusinessRule,
    ExecutiveSummaryContent,
)
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.llm.config import LLMConfig
from awa.llm.client import AzureLlamaClient, FakeLLMClient, set_default_llm_client, get_default_llm_client
from awa.llm.schemas import ToolFacts, WorkflowFacts, NarrativeResult
from awa.llm.cache import LLMNarrativeCache, compute_cache_key
from awa.llm.prompts import (
    TOOL_PROMPT_VERSION,
    TOOL_SYSTEM_PROMPT,
    WORKFLOW_PURPOSE_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    build_tool_user_prompt,
    build_workflow_purpose_user_prompt,
    build_executive_summary_user_prompt,
)
from awa.llm.generator import (
    LLMNarrativeGenerator,
    extract_tool_facts,
    extract_workflow_facts,
    set_default_generator,
    get_default_generator,
)
from awa.generators.docx_generator import generate_docx
from awa.generators.doc_builder import build_document_model
from backend.app.services.analyzer import to_diagram_dto, to_overview_dto


@pytest.fixture(autouse=True)
def reset_llm_defaults():
    """Ensure mock LLM client and clean generator are used during tests."""
    fake_client = FakeLLMClient(
        default_response="Aggregates and transforms claim record metrics for quarterly business reporting."
    )
    generator = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
    set_default_llm_client(fake_client)
    set_default_generator(generator)
    yield
    set_default_llm_client(None)
    set_default_generator(None)


# ---------------------------------------------------------------------------
# 1. Config & Security Tests
# ---------------------------------------------------------------------------

def test_llm_config_from_env(monkeypatch):
    monkeypatch.setenv("AZURE_ENDPOINT", "https://my-resource.services.ai.azure.com/models")
    monkeypatch.setenv("AZURE_LLAMAKEY", "super-secret-key-12345")
    monkeypatch.setenv("AZURE_DEPLOYMENT", "Llama-3.3-70B-Instruct")
    monkeypatch.setenv("AZURE_DEPLOYMENT_NAME", "Llama-3.3-70B-Instruct")

    cfg = LLMConfig.from_env()
    assert cfg.is_available() is True
    assert cfg.endpoint == "https://my-resource.services.ai.azure.com/models"
    assert cfg.deployment_name == "Llama-3.3-70B-Instruct"

    # Security: safe_repr must NEVER leak the secret key
    safe_str = cfg.safe_repr()
    assert "super-secret-key-12345" not in safe_str
    assert "SET (len=" in safe_str


def test_llm_config_missing_credentials(monkeypatch):
    monkeypatch.delenv("AZURE_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_LLAMAKEY", raising=False)
    monkeypatch.delenv("AZURE_DEPLOYMENT", raising=False)
    monkeypatch.delenv("AZURE_DEPLOYMENT_NAME", raising=False)

    cfg = LLMConfig.from_env()
    assert cfg.is_available() is False
    safe_str = cfg.safe_repr()
    assert "NOT SET" in safe_str


def test_missing_one_required_credential(monkeypatch):
    # Has endpoint and deployment, but missing key
    monkeypatch.setenv("AZURE_ENDPOINT", "https://my-resource.services.ai.azure.com/models")
    monkeypatch.delenv("AZURE_LLAMAKEY", raising=False)
    monkeypatch.setenv("AZURE_DEPLOYMENT", "Llama-3.3-70B-Instruct")

    cfg = LLMConfig.from_env()
    assert cfg.is_available() is False

    # Has key and deployment, but missing endpoint
    monkeypatch.delenv("AZURE_ENDPOINT", raising=False)
    monkeypatch.setenv("AZURE_LLAMAKEY", "some-key")
    cfg2 = LLMConfig.from_env()
    assert cfg2.is_available() is False


def test_azure_client_url_resolution():
    cfg_maas = LLMConfig(
        endpoint="https://my-resource.services.ai.azure.com/models",
        api_key="key",
        deployment="Llama",
    )
    client_maas = AzureLlamaClient(cfg_maas)
    assert client_maas._resolve_url() == "https://my-resource.services.ai.azure.com/models/chat/completions"

    cfg_oai = LLMConfig(
        endpoint="https://my-resource.openai.azure.com",
        api_key="key",
        deployment="Llama-33",
    )
    client_oai = AzureLlamaClient(cfg_oai)
    assert "openai/deployments/Llama-33/chat/completions" in client_oai._resolve_url()


def test_azure_client_graceful_failure_on_network_error():
    cfg = LLMConfig(
        endpoint="https://invalid-nonexistent-domain-123456789.com",
        api_key="key",
        deployment="Llama",
        timeout=1.0,
    )
    client = AzureLlamaClient(cfg)
    # Should not raise exception; must return None
    res = client.generate("system prompt", "user prompt")
    assert res is None


def test_api_key_never_appears_in_logs(monkeypatch, caplog):
    secret_key = "sk-super-secret-production-key-99999"
    monkeypatch.setenv("AZURE_ENDPOINT", "https://my-resource.services.ai.azure.com/models")
    monkeypatch.setenv("AZURE_LLAMAKEY", secret_key)
    monkeypatch.setenv("AZURE_DEPLOYMENT", "Llama")

    cfg = LLMConfig.from_env()
    client = AzureLlamaClient(cfg)

    with caplog.at_level(logging.DEBUG):
        # Trigger generation failure against bad URL
        client.generate("test system", "test user")
        # Check all log text
        for record in caplog.records:
            assert secret_key not in record.getMessage()


def test_api_key_never_appears_in_api_responses():
    secret_key = "sk-super-secret-key-12345"
    cfg = LLMConfig(
        endpoint="https://my-resource.services.ai.azure.com/models",
        api_key=secret_key,
        deployment="Llama",
    )
    client = AzureLlamaClient(cfg)
    diag = client.diagnose()
    # Diagnose dict must not contain the raw key
    assert secret_key not in str(diag)
    assert diag.get("key_configured") is True


# ---------------------------------------------------------------------------
# 2. Fact Extraction & Prompts Tests
# ---------------------------------------------------------------------------

def test_extract_tool_facts():
    wf = Workflow(metadata=WorkflowMetadata(name="Test Claims Workflow", version="2024.1"))
    tool = Tool(
        tool_id=16,
        plugin="AlteryxBasePluginsGui.Sort.Sort",
        tool_type="Sort",
        name="Sort Claims Descending",
        position=Position(100, 100),
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"fields": [{"field": "Quarter_End_Date", "order": "Desc"}]}),
        annotation="Sorts claims by Quarter End Date descending",
        container_name="Processing Container",
        output_fields=[Field(name="Claim_ID", type="Int64"), Field(name="Quarter_End_Date", type="Date")],
    )
    wf.tools[16] = tool

    facts = extract_tool_facts(wf, tool)
    assert facts.tool_id == 16
    assert facts.tool_type == "Sort"
    assert facts.workflow_role == "Ordering"
    assert facts.container_name == "Processing Container"
    assert "Quarter_End_Date" in str(facts.configuration_summary)
    assert "Claim_ID" in facts.output_fields

    prompt = build_tool_user_prompt(facts)
    assert "Tool ID:\n16" in prompt
    assert "Tool type:\nSort" in prompt
    assert "Quarter_End_Date" in prompt
    assert "GENERIC TOOL DEFINITION:" in prompt
    assert "WORKFLOW ROLE:\nOrdering" in prompt


def test_different_tool_instances_get_different_llm_context():
    wf = Workflow(metadata=WorkflowMetadata(name="Test Workflow", version="2024.1"))
    tool8 = Tool(
        tool_id=8,
        plugin="AlteryxBasePluginsGui.Summarize.Summarize",
        tool_type="Summarize",
        name="Summarize by Department",
        position=Position(100, 100),
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"summarize_fields": [{"field": "Department", "action": "GroupBy"}]}),
        annotation="Groups claims by department",
    )
    tool9 = Tool(
        tool_id=9,
        plugin="AlteryxBasePluginsGui.Summarize.Summarize",
        tool_type="Summarize",
        name="Summarize by Max Date",
        position=Position(200, 100),
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"summarize_fields": [{"field": "Claim_Date", "action": "Max"}]}),
        annotation="Computes latest claim date",
    )
    wf.tools[8] = tool8
    wf.tools[9] = tool9

    facts8 = extract_tool_facts(wf, tool8)
    facts9 = extract_tool_facts(wf, tool9)

    assert facts8.tool_id == 8
    assert facts9.tool_id == 9
    assert facts8.configuration_summary != facts9.configuration_summary

    prompt8 = build_tool_user_prompt(facts8)
    prompt9 = build_tool_user_prompt(facts9)
    assert prompt8 != prompt9
    assert "Department" in prompt8
    assert "Claim_Date" in prompt9


def test_extract_workflow_facts():
    wf = Workflow(metadata=WorkflowMetadata(name="Claims Volume Workflow", version="2024.1", description="ETL Pipeline"))
    bs = WorkflowBusinessSummary(
        business_purpose="Processes claim records to generate quarterly financial summaries.",
        one_line_purpose="Quarterly claims volume extract",
        why_it_matters="Critical financial reporting dataset",
        source_inputs=[
            BusinessInput(
                tool_id=1,
                name="Claims Ingest",
                raw_source="claims.xlsx",
                source_type="Excel Workbook",
                business_role="Primary dataset",
            )
        ],
        processing_stages=[
            BusinessStage(
                stage_number=1,
                name="Aggregation",
                short_title="AGG",
                summary="Summarizes quarterly counts",
                description="Aggregates data",
                tool_count=4,
            )
        ],
        business_outputs=[
            BusinessOutput(
                tool_id=17,
                name="Quarterly Summary",
                raw_destination="claims_summary.xlsx",
                destination_type="Excel",
                business_meaning="Executive quarterly reporting",
            )
        ],
    )

    wfacts = extract_workflow_facts(wf, bs)
    assert wfacts.name == "Claims Volume Workflow"
    assert len(wfacts.source_inputs) == 1
    assert len(wfacts.processing_stages) == 1
    assert len(wfacts.business_outputs) == 1
    assert wfacts.one_line_purpose == "Quarterly claims volume extract"

    p_prompt = build_workflow_purpose_user_prompt(wfacts)
    assert "Claims Ingest" in p_prompt
    assert "Quarterly Summary" in p_prompt

    e_prompt = build_executive_summary_user_prompt(wfacts)
    assert "Claims Volume Workflow" in e_prompt


# ---------------------------------------------------------------------------
# 3. Cache & Caching Guarantees Tests
# ---------------------------------------------------------------------------

def test_cache_workflow_isolation():
    cache = LLMNarrativeCache()

    key_wf1 = compute_cache_key("wf_claims_1", "tool_8", "2.0", "llama-70b", {"f": 1})
    key_wf2 = compute_cache_key("wf_claims_2", "tool_8", "2.0", "llama-70b", {"f": 2})

    assert key_wf1 != key_wf2

    res1 = NarrativeResult(text="Workflow 1 tool description", source="llm", model="llama-70b")
    cache.set(key_wf1, res1)

    assert cache.get(key_wf1).text == "Workflow 1 tool description"
    assert cache.get(key_wf2) is None


def test_llm_is_not_called_again_when_cached():
    call_count = 0

    def mock_gen(sys_prompt, usr_prompt):
        nonlocal call_count
        call_count += 1
        return "Generates quarterly summary statistics from input claim lines."

    fake_client = FakeLLMClient(generator_fn=mock_gen)
    cache = LLMNarrativeCache()
    generator = LLMNarrativeGenerator(client=fake_client, cache=cache)

    wf = Workflow(metadata=WorkflowMetadata(name="Test Workflow", version="2024.1"))
    tool = Tool(
        tool_id=1,
        plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
        tool_type="DbFileInput",
        name="Input Claims",
        position=Position(0, 0),
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={}),
        annotation="Reads claims data",
    )
    wf.tools[1] = tool

    # First call -> invokes generator
    r1 = generator.generate_tool_summary(wf, tool, workflow_id="wf_cache_test")
    assert r1.source == "llm"
    assert call_count == 1

    # Second call -> must return from cache without invoking generator
    r2 = generator.generate_tool_summary(wf, tool, workflow_id="wf_cache_test")
    assert r2.is_cached is True
    assert r2.text == r1.text
    assert call_count == 1


# ---------------------------------------------------------------------------
# 4. Generator & Fallback Tests
# ---------------------------------------------------------------------------

def test_llm_tool_summary_reaches_diagram_dto():
    fake_client = FakeLLMClient(
        response_map={
            "tool id:\n16": "Sorts claim records chronologically by Quarter End Date descending for reporting."
        }
    )
    generator = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
    set_default_generator(generator)

    sample_file = Path("tests/fixtures/sample_workflows/Demo_Claims_Volume_Extract.yxmd")
    if not sample_file.exists():
        sample_file = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")

    if not sample_file.exists():
        pytest.skip("Demo workflow fixture not found")

    res = analyze_canonical(sample_file)
    dto = to_diagram_dto(res)

    nodes_map = {n.tool_id: n for n in dto.nodes}
    if 16 in nodes_map:
        assert "Sorts claim records" in nodes_map[16].summary


def test_llm_business_purpose_reaches_overview_dto():
    fake_client = FakeLLMClient(
        response_map={
            "business purpose": "Automates end-to-end ingestion and analysis of insurance claims data across multiple operational reporting tables."
        }
    )
    generator = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
    set_default_generator(generator)

    sample_file = Path("tests/fixtures/sample_workflows/Demo_Claims_Volume_Extract.yxmd")
    if not sample_file.exists():
        sample_file = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")

    if not sample_file.exists():
        pytest.skip("Demo workflow fixture not found")

    res = analyze_canonical(sample_file)
    overview_dto = to_overview_dto(res)

    assert overview_dto.business_summary is not None
    assert "Automates end-to-end ingestion" in overview_dto.business_summary.business_purpose


def test_llm_executive_summary_reaches_docx(tmp_path):
    exec_text = "This report details the automated processing of insurance claims data across multiple calculation stages, delivering executive-ready volume extracts."
    fake_client = FakeLLMClient(
        response_map={
            "executive summary": exec_text
        }
    )
    generator = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
    set_default_generator(generator)

    wf = Workflow(metadata=WorkflowMetadata(name="Demo Claims Volume Extract", version="2024.1"))
    bs = WorkflowBusinessSummary(
        business_purpose="Automated claims reporting",
        one_line_purpose="Quarterly claims processing",
        why_it_matters="Executive reporting",
        executive_summary=ExecutiveSummaryContent(
            subject_and_purpose=exec_text,
            methods_and_process="Standard aggregation methods",
        ),
    )

    doc_model = build_document_model(
        workflow=wf,
        execution_order=[],
        translations={},
        dag_layout=None,
        lineage_paths=[],
        business_summary=bs,
        analysis_id="test_analysis_123",
    )

    docx_file = tmp_path / "executive_report.docx"
    generate_docx(doc_model, docx_file)

    assert docx_file.exists()
    assert docx_file.stat().st_size > 1000


def test_llm_failure_uses_deterministic_fallback():
    failing_client = FakeLLMClient(generator_fn=lambda s, u: None)
    generator = LLMNarrativeGenerator(client=failing_client, cache=LLMNarrativeCache())

    wf = Workflow(metadata=WorkflowMetadata(name="Test Workflow", version="2024.1"))
    tool = Tool(
        tool_id=1,
        plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
        tool_type="DbFileInput",
        name="Input Claims",
        position=Position(0, 0),
        configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={}),
        annotation="Claims_Volume_Extract_Demo.xlsx Sheet1",
    )
    wf.tools[1] = tool

    # Fallback must use tool registry summary, NOT the raw annotation
    result = generator.generate_tool_summary(wf, tool, workflow_id="test_wf")
    assert result.source == "deterministic_fallback"
    assert "Claims_Volume_Extract_Demo.xlsx Sheet1" not in result.text
    assert len(result.text) > 0


def test_azure_authentication_failure_is_logged_safely(monkeypatch, caplog):
    # Test that HTTP 401 or auth rejection is handled cleanly and logged safely
    cfg = LLMConfig(
        endpoint="https://httpbin.org/status/401",
        api_key="secret-auth-key-12345",
        deployment="Llama",
        timeout=2.0,
    )
    client = AzureLlamaClient(cfg)
    with caplog.at_level(logging.WARNING):
        res = client.generate("test", "test")
        assert res is None
        for record in caplog.records:
            assert "secret-auth-key-12345" not in record.getMessage()


# ---------------------------------------------------------------------------
# 5. Full End-to-End Pipeline & Multi-Instance Regression Tests
# ---------------------------------------------------------------------------

def test_full_pipeline_with_demo_workflow():
    sample_file = Path("tests/fixtures/sample_workflows/Demo_Claims_Volume_Extract.yxmd")
    if not sample_file.exists():
        sample_file = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")

    if not sample_file.exists():
        pytest.skip("Demo workflow fixture not found")

    captured_prompts: dict[int, str] = {}

    def mock_generator(system: str, user: str) -> str | None:
        if "Tool ID:\n8" in user:
            captured_prompts[8] = user
            return "Aggregates claim volume by quarter, claim status, manager, and examiner to create the manager/examiner-level reporting dataset used by downstream analysis."
        elif "Tool ID:\n9" in user:
            captured_prompts[9] = user
            return "Identifies the most recent quarter-end date from the summarized claims data so downstream processing can isolate the latest reporting period."
        elif "Tool ID:\n104" in user:
            captured_prompts[104] = user
            return "Computes quarterly claim volume subtotals by examiner."
        elif "Tool ID:\n16" in user:
            captured_prompts[16] = user
            return "Sorts quarterly claim metrics chronologically by quarter-end date in descending order."
        elif "Tool ID:\n1" in user:
            captured_prompts[1] = user
            return "Reads raw claims volume extract from Excel source file."
        elif "Tool ID:\n17" in user:
            captured_prompts[17] = user
            return "Exports finalized quarterly claims matrix to Excel deliverable."
        elif "business purpose" in system.lower() or "business purpose" in user.lower():
            return "Automates quarterly insurance claims volume extraction, summarization, and matrix reporting."
        elif "executive summary" in system.lower() or "executive summary" in user.lower():
            return "This workflow extracts claim volume data, performs multi-level aggregation by quarter and manager, and produces standardized reporting deliverables."
        return "Processes and transforms workflow record data."

    fake_client = FakeLLMClient(generator_fn=mock_generator)
    gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
    set_default_generator(gen)

    res = analyze_canonical(sample_file)
    overview_dto = to_overview_dto(res)
    diagram_dto = to_diagram_dto(res)

    # 1. Overview Business Purpose
    assert overview_dto.business_summary is not None
    assert "Automates quarterly insurance claims" in overview_dto.business_summary.business_purpose

    # 2. Tool "What It Does" in Diagram DTO
    nodes_by_id = {n.tool_id: n for n in diagram_dto.nodes}

    # Verify tool #8 and #9 received distinct summaries
    assert 8 in nodes_by_id and 9 in nodes_by_id
    assert nodes_by_id[8].summary != nodes_by_id[9].summary
    assert "manager" in nodes_by_id[8].summary.lower()
    assert "most recent quarter-end date" in nodes_by_id[9].summary.lower()

    # Verify that the prompts contain actual configuration details (not just generic info)
    assert 8 in captured_prompts
    assert "Quarter End Date" in captured_prompts[8]
    assert "Manager" in captured_prompts[8]
    assert "Examiner" in captured_prompts[8]

    # Verify tool #16 sort summary
    if 16 in nodes_by_id:
        assert "Sorts quarterly claim metrics" in nodes_by_id[16].summary
