"""Comprehensive offline test suite for LLM JSON parsing and extraction robustness.

Covers:
- JSON extractor multi-pass handling (direct, markdown fenced, surrounding prose, trailing commas,
  unicode BOM, thinking tags, unquoted python literals, empty/whitespace).
- Process Stages parsing resilience (syntax error recovery, tool coverage guarantee, fallback behavior, caching).
- Business Report parsing resilience (line 1 col 1 preamble recovery, schema validation, timeout, caching).
- LLM Client retry mechanism on transient HTTP 429/5xx and Timeout errors.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.request
import pytest
import networkx as nx

from awa.llm.config import LLMConfig
from awa.llm.client import FakeLLMClient, AzureLlamaClient
from awa.llm.cache import LLMNarrativeCache
from awa.llm.generator import LLMNarrativeGenerator
from awa.llm.json_extractor import extract_and_parse_json
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration
from awa.model.business_summary import (
    WorkflowBusinessSummary,
    BusinessInput,
    BusinessOutput,
    BusinessStage,
    BusinessRule,
    BusinessLineageEntry,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

def create_sample_workflow() -> tuple[Workflow, nx.DiGraph, WorkflowBusinessSummary]:
    """Create a minimal 3-tool workflow for testing."""
    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="Customer Churn Pipeline",
            version="2024.1",
            description="Predicts customer churn and outputs summary dataset",
            content_hash="hash_test_12345",
        )
    )

    t1 = Tool(
        tool_id=1,
        plugin="DbFileInput",
        tool_type="DbFileInput",
        name="Input Customers",
        position=None,
        annotation="Read customer profile records",
        configuration=ToolConfiguration(raw_xml="<Configuration />", parsed={"file_name": "customers.csv"}),
    )
    t2 = Tool(
        tool_id=2,
        plugin="Formula",
        tool_type="Formula",
        name="Compute Risk",
        position=None,
        annotation="Calculate churn risk score",
        configuration=ToolConfiguration(raw_xml="<Configuration />", parsed={"formula_fields": [{"field": "RiskScore", "expression": "Tenure * 0.5"}]}),
    )
    t3 = Tool(
        tool_id=3,
        plugin="DbFileOutput",
        tool_type="DbFileOutput",
        name="Output Deliverable",
        position=None,
        annotation="Write high risk customers",
        configuration=ToolConfiguration(raw_xml="<Configuration />", parsed={"file_name": "high_risk.csv"}),
    )

    workflow.tools = {1: t1, 2: t2, 3: t3}

    graph = nx.DiGraph()
    graph.add_edge(1, 2)
    graph.add_edge(2, 3)

    summary = WorkflowBusinessSummary(
        business_purpose="Identifies high-risk customer segments to support proactive retention initiatives.",
        one_line_purpose="Customer Churn Pipeline",
        why_it_matters="Identifies retention opportunities",
        business_function="Customer Retention",
        source_inputs=[
            BusinessInput(
                tool_id=1,
                name="customers.csv",
                raw_source="customers.csv",
                source_type="CSV File",
                business_role="Primary customer demographic and transactional profile data.",
                dependency_significance="Essential source required for customer risk calculations.",
            )
        ],
        business_outputs=[
            BusinessOutput(
                tool_id=3,
                name="high_risk.csv",
                raw_destination="high_risk.csv",
                destination_type="CSV File",
                business_meaning="Delivers segmented customer records prioritized for retention intervention.",
                likely_use="Utilized by customer success teams to deploy targeted retention workflows.",
            )
        ],
        business_rules=[
            BusinessRule(
                rule_name="RiskScore Calculation",
                description="Calculates customer risk using tenure weighting.",
                category="Calculation",
            )
        ],
        lineage=[
            BusinessLineageEntry(
                source_name="customers.csv",
                target_name="high_risk.csv",
                transformation="Derives risk scores and exports high-risk cohort.",
            )
        ],
    )

    return workflow, graph, summary


SAMPLE_BUSINESS_REPORT_DICT = {
    "workflow_title": "Customer Churn Pipeline",
    "workflow_description": "Predicts customer churn and outputs summary dataset",
    "executive_summary": "This automated workflow processes customer demographic and behavioral data to derive risk scores and publish prioritized retention targets for operational teams.",
    "methods_of_analysis": "The pipeline utilizes deterministic formula calculations, tenure weighting transformations, and relational cohort filtering to identify retention risks.",
    "findings": [
        "Customer profile attributes are ingested and standardized across all active accounts.",
        "Tenure metrics are evaluated to establish weighted churn propensity scores.",
        "High-risk accounts are partitioned into a dedicated operational export dataset.",
    ],
    "conclusions": "The analysis establishes an objective, automated risk baseline enabling customer success teams to proactively target at-risk cohorts.",
    "inputs": [
        {
            "source_dataset": "customers.csv",
            "business_role": "Customer profile and tenure repository",
            "source_format": "CSV File",
            "dependency_significance": "Essential baseline input",
        }
    ],
    "outputs": [
        {
            "output_deliverable": "high_risk.csv",
            "what_it_represents": "Prioritized high-risk customer records",
            "business_use": "Customer retention campaign deployment",
            "destination_format": "CSV File",
        }
    ],
    "sequential_stages": [
        {
            "stage_number": 1,
            "stage_name": "Customer Profile Ingestion",
            "description": "Ingests customer profile records from CSV.",
            "operational_explanation": "Reads raw CSV data into memory stream.",
        },
        {
            "stage_number": 2,
            "stage_name": "Churn Risk Calculation",
            "description": "Calculates tenure-weighted churn risk metrics.",
            "operational_explanation": "Evaluates formula expressions across customer attributes.",
        },
        {
            "stage_number": 3,
            "stage_name": "High Risk Cohort Export",
            "description": "Publishes high-risk customer records to CSV.",
            "operational_explanation": "Writes finalized dataset to storage destination.",
        },
    ],
    "business_rules": [
        {
            "business_rule": "RiskScore = Tenure * 0.5",
            "category": "Derivation",
            "evidence_configuration": "Formula Tool #2",
        }
    ],
    "lineage": [
        {
            "source_datasets": "customers.csv",
            "major_business_transformation": "Tenure risk scoring and filtering",
            "target_deliverable": "high_risk.csv",
        }
    ],
}


# ---------------------------------------------------------------------------
# 1. JSON Extractor Unit Tests
# ---------------------------------------------------------------------------

class TestJSONExtractor:
    """Test suite for the shared extract_and_parse_json function."""

    def test_direct_valid_dict(self):
        payload = {"key": "value", "count": 42}
        raw = json.dumps(payload)
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == payload
        assert mode == "success"
        assert err == ""

    def test_direct_valid_list(self):
        payload = [{"a": 1}, {"b": 2}]
        raw = json.dumps(payload)
        data, mode, err = extract_and_parse_json(raw, expected_type=list)
        assert data == payload
        assert mode == "success"
        assert err == ""

    def test_markdown_code_fence_json(self):
        raw = '```json\n{"stage_name": "Ingestion", "tools": [1, 2]}\n```'
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"stage_name": "Ingestion", "tools": [1, 2]}
        assert mode == "success"

    def test_markdown_code_fence_no_lang(self):
        raw = '```\n{"key": "val"}\n```'
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"key": "val"}
        assert mode == "success"

    def test_surrounding_prose_before_and_after(self):
        raw = (
            "Here is the requested Business Report:\n\n"
            "```json\n"
            '{"workflow_title": "Demo Pipeline", "items": [1, 2, 3]}\n'
            "```\n\n"
            "I hope this helps your analysis!"
        )
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"workflow_title": "Demo Pipeline", "items": [1, 2, 3]}
        assert mode == "success"

    def test_balanced_scanner_unfenced_with_preamble(self):
        raw = (
            "Based on the analysis, here is the result: "
            '{"stages": [{"stage_name": "Step 1", "tool_ids": [1]}], "version": 1} '
            "Let me know if you need changes."
        )
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"stages": [{"stage_name": "Step 1", "tool_ids": [1]}], "version": 1}
        assert mode == "success"

    def test_trailing_comma_normalization(self):
        # Simulates: Expecting ',' delimiter error due to trailing commas in objects or lists
        raw = """
        {
            "stages": [
                {
                    "stage_name": "Ingest",
                    "category": "INGESTION",
                    "tool_ids": [1, 2, ],
                },
            ],
        }
        """
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data is not None
        assert "stages" in data
        assert len(data["stages"]) == 1
        assert data["stages"][0]["tool_ids"] == [1, 2]

    def test_unicode_bom_and_think_tags(self):
        raw = '\ufeff<think>Let me construct the business report JSON step by step.</think>{"title": "BOM Test"}'
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"title": "BOM Test"}

    def test_unquoted_python_literals(self):
        raw = '{"active": True, "archived": False, "notes": None}'
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data == {"active": True, "archived": False, "notes": None}

    def test_empty_and_whitespace_inputs(self):
        for empty_val in [None, "", "   ", "\n\t\n"]:
            data, mode, err = extract_and_parse_json(empty_val, expected_type=dict)
            assert data is None
            assert mode == "empty_response"
            assert "empty" in err.lower() or "none" in err.lower()

    def test_pure_prose_no_json(self):
        raw = "I cannot generate a JSON report for this workflow because no tools are present."
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data is None
        assert mode == "extraction_failed"

    def test_expected_type_mismatch(self):
        raw = '["item1", "item2"]'
        # Expect dict, got list
        data, mode, err = extract_and_parse_json(raw, expected_type=dict)
        assert data is None
        assert mode in ("type_mismatch", "json_parse_failed")


# ---------------------------------------------------------------------------
# 2. Process Stages Resilience Tests
# ---------------------------------------------------------------------------

class TestProcessStagesRobustness:
    """Test suite for generate_process_stages and _parse_process_stages_json."""

    def test_process_stages_clean_json(self):
        workflow, graph, summary = create_sample_workflow()
        stages_payload = {
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Customer Profile Ingestion",
                    "category": "INGESTION",
                    "description": "Reads source files",
                    "purpose": "Source ingestion",
                    "transformation": "Direct ingest",
                    "key_actions": ["Read customers.csv"],
                    "tool_ids": [1],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Tenure Risk Calculation",
                    "category": "CALCULATION",
                    "description": "Applies churn formulas",
                    "purpose": "Risk scoring",
                    "transformation": "Formula calculation",
                    "key_actions": ["Compute RiskScore"],
                    "tool_ids": [2],
                },
                {
                    "stage_number": 3,
                    "stage_name": "High Risk Output",
                    "category": "REPORTING",
                    "description": "Writes destination files",
                    "purpose": "Deliverable publication",
                    "transformation": "Direct export",
                    "key_actions": ["Export high_risk.csv"],
                    "tool_ids": [3],
                },
            ]
        }
        client = FakeLLMClient(response=json.dumps(stages_payload))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary, workflow_id="test_wf")
        assert len(stages) == 3
        assert stages[0].name == "Customer Profile Ingestion"
        assert stages[0].tool_ids == [1]
        assert stages[1].tool_ids == [2]
        assert stages[2].tool_ids == [3]

        # Verify cache HIT on second call
        cached_stages = gen.generate_process_stages(workflow, graph, summary, workflow_id="test_wf")
        assert len(cached_stages) == 3
        assert len(client.calls) == 1  # No additional LLM call

    def test_process_stages_recovers_from_delimiter_syntax_error(self):
        """Simulates: [LLM] Error parsing process stages JSON: Expecting ',' delimiter line 6 column 5."""
        workflow, graph, summary = create_sample_workflow()
        malformed_response = """
        {
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Customer Data Ingestion",
                    "category": "INGESTION",
                    "description": "Ingests raw records",
                    "purpose": "Data intake",
                    "transformation": "Direct load",
                    "key_actions": ["Ingest customer file", ],
                    "tool_ids": [1, ],
                },
                {
                    "stage_number": 2,
                    "stage_name": "Risk Scoring & Export",
                    "category": "PROCESSING",
                    "description": "Scores and exports",
                    "purpose": "Output generation",
                    "transformation": "Calculation and export",
                    "key_actions": ["Score tenure", "Write high_risk.csv"],
                    "tool_ids": [2, 3],
                }
            ]
        }
        """
        client = FakeLLMClient(response=malformed_response)
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary, workflow_id="test_wf_syntax_err")
        assert len(stages) == 2
        assert stages[0].name == "Customer Data Ingestion"
        assert stages[0].tool_ids == [1]
        assert stages[1].tool_ids == [2, 3]

    def test_process_stages_markdown_wrapped_with_preamble(self):
        workflow, graph, summary = create_sample_workflow()
        response_text = (
            "Here is the stage breakdown for the workflow:\n\n"
            "```json\n"
            "{\n"
            '  "stages": [\n'
            '    {\n'
            '      "stage_number": 1,\n'
            '      "stage_name": "Source Ingestion",\n'
            '      "category": "INGESTION",\n'
            '      "description": "Reads source datasets",\n'
            '      "purpose": "Ingestion",\n'
            '      "transformation": "None",\n'
            '      "key_actions": ["Read data"],\n'
            '      "tool_ids": [1, 2, 3]\n'
            '    }\n'
            "  ]\n"
            "}\n"
            "```\n"
        )
        client = FakeLLMClient(response=response_text)
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary)
        assert len(stages) == 1
        assert stages[0].name == "Source Ingestion"
        assert stages[0].tool_ids == [1, 2, 3]

    def test_process_stages_tool_coverage_guarantee(self):
        """Verify that tools omitted by the LLM are automatically assigned to maintain 100% coverage."""
        workflow, graph, summary = create_sample_workflow()
        # LLM only assigns tool 1; tools 2 and 3 are omitted
        partial_payload = {
            "stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Ingestion Stage",
                    "category": "INGESTION",
                    "description": "Loads data",
                    "purpose": "Data load",
                    "transformation": "Direct",
                    "key_actions": ["Load"],
                    "tool_ids": [1],
                }
            ]
        }
        client = FakeLLMClient(response=json.dumps(partial_payload))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary)
        all_assigned = [tid for stg in stages for tid in stg.tool_ids]
        assert set(all_assigned) == {1, 2, 3}

    def test_process_stages_empty_response_triggers_deterministic_fallback(self):
        workflow, graph, summary = create_sample_workflow()
        client = FakeLLMClient(response="")
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary, workflow_id="empty_wf")
        assert len(stages) >= 1
        # Confirm fallback is NOT cached
        assert cache.count() == 0

    def test_process_stages_unparseable_prose_triggers_deterministic_fallback(self):
        workflow, graph, summary = create_sample_workflow()
        client = FakeLLMClient(response="I am unable to parse this workflow.")
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        stages = gen.generate_process_stages(workflow, graph, summary, workflow_id="prose_wf")
        assert len(stages) >= 1
        # Fallback should not be cached
        assert cache.count() == 0


# ---------------------------------------------------------------------------
# 3. Business Report Robustness Tests
# ---------------------------------------------------------------------------

class TestBusinessReportRobustness:
    """Test suite for generate_business_report and _parse_business_report_json."""

    def test_business_report_clean_json(self):
        workflow, graph, summary = create_sample_workflow()
        client = FakeLLMClient(response=json.dumps(SAMPLE_BUSINESS_REPORT_DICT))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        report = gen.generate_business_report(workflow, summary, graph, workflow_id="br_clean")
        assert report is not None
        assert report.workflow_title == "Customer Churn Pipeline"
        assert len(report.findings) == 3
        assert len(report.inputs) == 1
        assert len(report.outputs) == 1
        assert len(report.sequential_stages) == 3

        # Verify cache HIT on second invocation
        report2 = gen.generate_business_report(workflow, summary, graph, workflow_id="br_clean")
        assert report2 is not None
        assert len(client.calls) == 1

    def test_business_report_recovers_from_line_1_col_1_preamble_error(self):
        """Simulates: Failed to parse Business Report JSON response: Expecting value line 1 column 1."""
        workflow, graph, summary = create_sample_workflow()
        preamble_response = (
            "Here is the Executive Business Report generated from the workflow facts:\n\n"
            "```json\n"
            + json.dumps(SAMPLE_BUSINESS_REPORT_DICT, indent=2)
            + "\n```\n\n"
            "This report satisfies all analytical governance criteria."
        )
        client = FakeLLMClient(response=preamble_response)
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        report = gen.generate_business_report(workflow, summary, graph, workflow_id="br_preamble")
        assert report is not None
        assert report.workflow_title == "Customer Churn Pipeline"
        assert len(report.findings) == 3

    def test_business_report_empty_returns_none_and_no_cache(self):
        workflow, graph, summary = create_sample_workflow()
        client = FakeLLMClient(response="")
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        report = gen.generate_business_report(workflow, summary, graph, workflow_id="br_empty")
        assert report is None
        assert cache.count() == 0

    def test_business_report_rejects_empty_executive_summary(self):
        workflow, graph, summary = create_sample_workflow()
        bad_payload = dict(SAMPLE_BUSINESS_REPORT_DICT)
        bad_payload["executive_summary"] = "Too short"
        client = FakeLLMClient(response=json.dumps(bad_payload))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        report = gen.generate_business_report(workflow, summary, graph, workflow_id="br_short_exec")
        assert report is None
        assert cache.count() == 0

    def test_business_report_rejects_empty_findings(self):
        workflow, graph, summary = create_sample_workflow()
        bad_payload = dict(SAMPLE_BUSINESS_REPORT_DICT)
        bad_payload["findings"] = []
        client = FakeLLMClient(response=json.dumps(bad_payload))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        report = gen.generate_business_report(workflow, summary, graph, workflow_id="br_no_findings")
        assert report is None
        assert cache.count() == 0

    def test_business_report_timeout_passed_to_client(self):
        """Verify that business_report_timeout (60.0s) is passed to LLM client."""
        workflow, graph, summary = create_sample_workflow()
        client = FakeLLMClient(response=json.dumps(SAMPLE_BUSINESS_REPORT_DICT))
        cache = LLMNarrativeCache()
        gen = LLMNarrativeGenerator(client=client, cache=cache)

        gen.generate_business_report(workflow, summary, graph, workflow_id="br_timeout_test")
        assert len(client.calls) == 1
        assert client.calls[0]["timeout"] == 60.0


# ---------------------------------------------------------------------------
# 4. LLM Client Transient Retry Tests
# ---------------------------------------------------------------------------

class TestLLMClientRetryMechanics:
    """Test suite for client retry loop on transient HTTP 429/5xx and Timeout errors."""

    def test_client_retries_on_http_429_then_succeeds(self):
        config = LLMConfig(
            endpoint="https://mock.azure.com/v1/chat/completions",
            api_key="test_key",
            deployment="mock-model",
            retry_attempts=2,
            retry_backoff_base=0.01,
        )
        client = AzureLlamaClient(config=config)

        # Mock urllib.request.urlopen to fail once with HTTP 429, then succeed with 200
        mock_resp_success = MagicMock()
        mock_resp_success.status = 200
        mock_resp_success.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"status": "ok"}'}}]
        }).encode("utf-8")
        mock_resp_success.__enter__.return_value = mock_resp_success

        err_429 = urllib.error.HTTPError(
            url="https://mock.azure.com",
            code=429,
            msg="Rate limit exceeded",
            hdrs={},  # type: ignore
            fp=None,  # type: ignore
        )

        with patch("urllib.request.urlopen", side_effect=[err_429, mock_resp_success]):
            response = client.generate("system prompt", "user prompt")
            assert response == '{"status": "ok"}'

    def test_client_retries_on_http_503_then_succeeds(self):
        config = LLMConfig(
            endpoint="https://mock.azure.com/v1/chat/completions",
            api_key="test_key",
            deployment="mock-model",
            retry_attempts=2,
            retry_backoff_base=0.01,
        )
        client = AzureLlamaClient(config=config)

        mock_resp_success = MagicMock()
        mock_resp_success.status = 200
        mock_resp_success.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"result": 100}'}}]
        }).encode("utf-8")
        mock_resp_success.__enter__.return_value = mock_resp_success

        err_503 = urllib.error.HTTPError(
            url="https://mock.azure.com",
            code=503,
            msg="Service Unavailable",
            hdrs={},  # type: ignore
            fp=None,  # type: ignore
        )

        with patch("urllib.request.urlopen", side_effect=[err_503, mock_resp_success]):
            response = client.generate("system prompt", "user prompt")
            assert response == '{"result": 100}'

    def test_client_retries_on_timeout_then_succeeds(self):
        config = LLMConfig(
            endpoint="https://mock.azure.com/v1/chat/completions",
            api_key="test_key",
            deployment="mock-model",
            retry_attempts=2,
            retry_backoff_base=0.01,
        )
        client = AzureLlamaClient(config=config)

        mock_resp_success = MagicMock()
        mock_resp_success.status = 200
        mock_resp_success.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"report": "generated"}'}}]
        }).encode("utf-8")
        mock_resp_success.__enter__.return_value = mock_resp_success

        with patch("urllib.request.urlopen", side_effect=[TimeoutError("Request timed out"), mock_resp_success]):
            response = client.generate("system prompt", "user prompt", timeout=60.0)
            assert response == '{"report": "generated"}'

    def test_client_exhausts_retries_and_returns_none(self):
        config = LLMConfig(
            endpoint="https://mock.azure.com/v1/chat/completions",
            api_key="test_key",
            deployment="mock-model",
            retry_attempts=2,
            retry_backoff_base=0.01,
        )
        client = AzureLlamaClient(config=config)

        err_500 = urllib.error.HTTPError(
            url="https://mock.azure.com",
            code=500,
            msg="Internal Server Error",
            hdrs={},  # type: ignore
            fp=None,  # type: ignore
        )

        with patch("urllib.request.urlopen", side_effect=[err_500, err_500, err_500]):
            response = client.generate("system prompt", "user prompt")
            assert response is None
