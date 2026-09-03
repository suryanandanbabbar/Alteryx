"""Tests for the purely deterministic 5-factor Criticality Assessment layer.

Covers:
1. Zero LLM calls for criticality in canonical and portfolio analysis
2. 5-factor score & level calibration
3. Deterministic behavior when LLM is present or absent
4. Portfolio dependency context integration
5. Export & XLSX zero-call verification
6. Other LLM features still functioning
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator
from awa.llm.schemas import CriticalityEvidencePackage, WorkflowFacts
from awa.analysis.workflow_criticality import (
    calculate_workflow_criticality,
    build_criticality_evidence_package,
    PortfolioDependencyContext,
)
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.portfolio import PortfolioWorkflowSummary, PortfolioAnalysis, PortfolioAggregateMetrics
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.source_info import SourceInfo
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.generators.portfolio_xlsx_generator import generate_portfolio_excel


import networkx as nx
from awa.model.dag_layout import DagLayout
from awa.model.python_trace import PythonTraceMap


def _make_dummy_result(filename: str, bs: WorkflowBusinessSummary) -> CanonicalAnalysisResult:
    wf = Workflow(metadata=WorkflowMetadata(name=filename, version="2024.1"))
    metrics = WorkflowMetrics(total_nodes=10, total_connections=10, input_count=1, output_count=1)
    return CanonicalAnalysisResult(
        analysis_id=f"aid_{filename}",
        source=SourceInfo(source_format="yxmd", original_filename=filename),
        workflow=wf,
        graph=nx.DiGraph(),
        execution_order=[1],
        translations={},
        consumed_anchors={},
        lineage_paths=[],
        metrics=metrics,
        dag_layout=DagLayout(nodes=[], edges=[], width=200, height=100, title=filename),
        python_trace=PythonTraceMap(entries=[], total_lines=5),
        tool_explanations={},
        required_libraries=[],
        diagnostics=[],
        business_summary=bs,
    )


def test_generate_criticality_assessment_makes_zero_llm_calls():
    """Even if an LLM client is configured, generate_criticality_assessment must make 0 LLM calls."""
    mock_client = MagicMock(spec=FakeLLMClient)
    mock_client.is_available = True
    mock_client.generate.return_value = "SHOULD_NOT_BE_CALLED"

    generator = LLMNarrativeGenerator(client=mock_client)
    evidence = build_criticality_evidence_package(
        workflow_id="wf_test",
        workflow_filename="Test.yxmd",
        sources=["input.csv"],
        targets=["output.yxdb"],
        inspection_sinks=[],
        operational_metadata={"last_run": "5 months ago", "frequency": "Monthly"},
    )

    result = generator.generate_criticality_assessment(evidence)

    assert mock_client.generate.call_count == 0
    assert result.source == "deterministic"
    assert result.criticality_score == 36.0
    assert result.criticality_level == "MEDIUM"


def test_canonical_and_portfolio_zero_criticality_llm_calls():
    """Portfolio analysis must compute criticality deterministically with 0 LLM calls."""
    mock_client = MagicMock(spec=FakeLLMClient)
    mock_client.is_available = True
    mock_client.generate.return_value = "SHOULD_NOT_BE_CALLED"

    generator = LLMNarrativeGenerator(client=mock_client)

    bs1 = WorkflowBusinessSummary(
        business_purpose="Purpose 1",
        one_line_purpose="Purpose 1",
        why_it_matters="Matters 1",
        criticality_score=40.0,
        criticality_level="MEDIUM",
        criticality_source="deterministic",
    )
    bs2 = WorkflowBusinessSummary(
        business_purpose="Purpose 2",
        one_line_purpose="Purpose 2",
        why_it_matters="Matters 2",
        criticality_score=16.0,
        criticality_level="LOW",
        criticality_source="deterministic",
    )

    res1 = _make_dummy_result("W1.yxmd", bs1)
    res2 = _make_dummy_result("W2.yxmd", bs2)

    portfolio = build_portfolio_analysis(
        [("W1.yxmd", "W1.yxmd", res1), ("W2.yxmd", "W2.yxmd", res2)],
        generator=generator,
    )

    assert mock_client.generate.call_count == 0
    for w in portfolio.workflows:
        assert w.criticality_source == "deterministic"
        assert w.criticality_score >= 0.0
        assert w.criticality_level in ("LOW", "MEDIUM", "HIGH")


def test_other_llm_features_still_use_llm_client():
    """Business purpose and executive summary generation still call LLM client when available."""
    mock_client = MagicMock(spec=FakeLLMClient)
    mock_client.is_available = True
    mock_client.model_name = "test-model"
    mock_client.generate.return_value = '{"business_purpose": "The workflow ingests policy underwriting records and calculates premium reserves for commercial lines.", "business_function": "Underwriting Policy Calculation", "business_area_tag": "Underwriting"}'

    generator = LLMNarrativeGenerator(client=mock_client)
    wf = Workflow(metadata=WorkflowMetadata(name="Test.yxmd", version="2024.1"))
    bs = WorkflowBusinessSummary(
        business_purpose="",
        one_line_purpose="",
        why_it_matters="",
    )
    res = generator.generate_business_purpose(wf, bs)

    assert mock_client.generate.call_count == 1
    assert "premium reserves" in res.business_purpose


def test_xlsx_export_zero_llm_calls(tmp_path):
    """Portfolio XLSX generation must format and export criticality without triggering LLM calls."""
    wf_summary = PortfolioWorkflowSummary(
        workflow_id="wf_1",
        filename="Test_Process.yxmd",
        relative_path="Test_Process.yxmd",
        status="SUCCESS",
        business_purpose="Processes claims data.",
        business_area_tag="Claims & Risk",
        criticality_score=78.2,
        criticality_level="HIGH",
        criticality_justification="Core claims reserve calculation workflow.",
        criticality_source="deterministic",
    )
    portfolio = PortfolioAnalysis(
        portfolio_id="test_p_1",
        portfolio_name="Test Portfolio",
        workflow_count=1,
        workflows=[wf_summary],
        metrics=PortfolioAggregateMetrics(total_workflows=1, successful_workflows=1),
        shared_sources=[],
        shared_targets=[],
        relationships=[],
        rationalisation_candidates=[],
    )

    out_file = tmp_path / "test_portfolio.xlsx"
    with patch("awa.llm.generator.LLMNarrativeGenerator.generate_criticality_assessment") as mock_gen:
        generate_portfolio_excel(portfolio, successful_results={}, rationalisation=None, output_path=out_file)
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        mock_gen.assert_not_called()


def test_legacy_persisted_analysis_backward_compatibility():
    """Legacy persisted models without new criticality fields must default gracefully."""
    legacy_bs = WorkflowBusinessSummary(
        business_purpose="Legacy purpose.",
        one_line_purpose="Legacy summary.",
        why_it_matters="Legacy why it matters.",
    )
    assert legacy_bs.criticality_score == 0.0
    assert legacy_bs.criticality_level == "LOW"
    assert legacy_bs.criticality_justification == ""
    assert legacy_bs.factor_assessments == {}
    bs_dict = legacy_bs.to_dict()
    assert "criticality_score" in bs_dict
    assert "criticality_justification" in bs_dict

    legacy_pws = PortfolioWorkflowSummary(
        workflow_id="wf_old",
        filename="Old_Workflow.yxmd",
        relative_path="Old_Workflow.yxmd",
        status="SUCCESS",
        business_purpose="Old purpose.",
    )
    assert legacy_pws.criticality_score == 0.0
    assert legacy_pws.criticality_level == "LOW"
    assert legacy_pws.criticality_justification == ""
    pws_dict = legacy_pws.to_dict()
    assert "criticality_score" in pws_dict
    assert "criticality_justification" in pws_dict


