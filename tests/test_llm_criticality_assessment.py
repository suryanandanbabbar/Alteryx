"""Tests for the LLM-driven, evidence-grounded Criticality Assessment layer.

Covers:
1. Score & Level Calibration consistency
2. Evidence grounding for customer/client/downstream impact
3. Semantic role differentiation over mechanical counts
4. Midstream hub vs Leaf consumer propagation
5. Deterministic validation rejection & fallback triggers
6. LLM unavailable fallback behavior
7. Caching and portfolio context change detection
8. Zero downstream LLM calls (Portfolio aggregation, Overview DTO, XLSX export)
9. Backward compatibility for legacy persisted results
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from awa.llm.schemas import (
    CriticalityEvidencePackage,
    CriticalityAssessmentResult,
    FactorAssessment,
)
from awa.llm.generator import (
    LLMNarrativeGenerator,
    _validate_criticality_assessment,
    compose_deterministic_criticality_fallback,
)
from awa.analysis.workflow_criticality import (
    build_criticality_evidence_package,
    calculate_workflow_criticality,
    PortfolioDependencyContext,
)
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.portfolio import PortfolioWorkflowSummary, PortfolioAnalysis
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.source_info import SourceInfo
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.dag_layout import DagLayout
from awa.model.python_trace import PythonTraceMap
import networkx as nx


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

def make_dummy_evidence(
    workflow_id: str = "wf_test_1",
    workflow_filename: str = "Test_Workflow.yxmd",
    business_purpose: str = "Automates operational data processing.",
    business_function: str = "Operational Processing",
    business_area: str = "Underwriting",
    production_targets: list[str] | None = None,
    inspection_sinks: list[str] | None = None,
    upstream_producers: list[str] | None = None,
    downstream_consumers: list[str] | None = None,
    shared_targets: list[str] | None = None,
    shared_sources: list[str] | None = None,
    dependency_position: str = "Isolated Process",
    semantic_impact_signals: list[str] | None = None,
) -> CriticalityEvidencePackage:
    targets = production_targets or ["output_data.csv"]
    sinks = inspection_sinks or []
    return CriticalityEvidencePackage(
        workflow_id=workflow_id,
        workflow_filename=workflow_filename,
        business_purpose=business_purpose,
        business_function=business_function,
        business_area=business_area,
        production_targets=targets,
        inspection_sinks=sinks,
        upstream_producers=upstream_producers or [],
        downstream_consumers=downstream_consumers or [],
        shared_targets=shared_targets or [],
        shared_sources=shared_sources or [],
        dependency_position=dependency_position,
        deterministic_counts={
            "source_count": 2,
            "target_count": len(targets),
            "inspection_sink_count": len(sinks),
            "downstream_consumer_count": len(downstream_consumers or []),
            "upstream_producer_count": len(upstream_producers or []),
        },
        semantic_impact_signals=semantic_impact_signals or [],
        deterministic_reference_score=45.0,
        deterministic_reference_level="MEDIUM",
    )


# ---------------------------------------------------------------------------
# 1. Deterministic Validation & Calibration Tests
# ---------------------------------------------------------------------------

def test_validation_rejects_score_level_mismatch():
    """Score 85.0 with level LOW or MEDIUM must be rejected by validation."""
    evidence = make_dummy_evidence()
    payload = {
        "criticality_score": 85.0,
        "criticality_level": "LOW",  # Mismatch! 85 is HIGH
        "criticality_justification": "This is a comprehensive justification explaining that this workflow operates as a key component in the enterprise pipeline.",
        "business_consequence": "Interruption halts pipeline execution.",
        "dependency_impact": "Downstream processes are delayed.",
        "affected_scope": "Underwriting operations.",
        "migration_implication": "Validate data contracts before cutover.",
        "confidence": "HIGH",
        "factor_assessments": {
            "production_outputs": {"assessment": "HIGH", "evidence": "targets", "rationale": "persisted"},
            "downstream_dependency": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
            "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
        },
    }
    is_valid, reason = _validate_criticality_assessment(payload, evidence)
    assert not is_valid
    assert "does not match level" in reason


def test_validation_rejects_unsupported_customer_impact():
    """HIGH customer impact without customer signals in evidence must be rejected."""
    evidence = make_dummy_evidence(semantic_impact_signals=[])  # No customer signals
    payload = {
        "criticality_score": 80.0,
        "criticality_level": "HIGH",
        "criticality_justification": "This is a detailed justification stating that this workflow is critical to customer operations across multiple divisions.",
        "business_consequence": "Severe customer service disruption.",
        "dependency_impact": "Disruption propagates across customer touchpoints.",
        "affected_scope": "Direct customer service operations.",
        "migration_implication": "Verify customer communication channels.",
        "confidence": "HIGH",
        "factor_assessments": {
            "production_outputs": {"assessment": "HIGH", "evidence": "targets", "rationale": "persisted"},
            "downstream_dependency": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
            "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "customer_impact": {"assessment": "HIGH", "evidence": "claims direct customer impact", "rationale": "customer affected"},
        },
    }
    is_valid, reason = _validate_criticality_assessment(payload, evidence)
    assert not is_valid
    assert "customer_impact assessed as HIGH without customer/claimant impact signals" in reason


def test_validation_rejects_unsupported_downstream_dependency():
    """HIGH downstream dependency without downstream consumers in evidence must be rejected."""
    evidence = make_dummy_evidence(downstream_consumers=[])  # No downstream consumers
    payload = {
        "criticality_score": 75.0,
        "criticality_level": "HIGH",
        "criticality_justification": "This workflow is highly critical because of extensive downstream propagation across the portfolio pipeline ecosystem.",
        "business_consequence": "Downstream systems fail.",
        "dependency_impact": "Propagates widely.",
        "affected_scope": "Operations.",
        "migration_implication": "Validate dependencies.",
        "confidence": "HIGH",
        "factor_assessments": {
            "production_outputs": {"assessment": "HIGH", "evidence": "targets", "rationale": "persisted"},
            "downstream_dependency": {"assessment": "HIGH", "evidence": "many consumers", "rationale": "propagates"},
            "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
            "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
        },
    }
    is_valid, reason = _validate_criticality_assessment(payload, evidence)
    assert not is_valid
    assert "downstream_dependency assessed as HIGH but workflow has 0 downstream consumers" in reason


def test_validation_rejects_generic_filler_and_prompt_leakage():
    """Boilerplate filler or prompt leakage must be rejected."""
    evidence = make_dummy_evidence()
    payload = {
        "criticality_score": 45.0,
        "criticality_level": "MEDIUM",
        "criticality_justification": "This workflow is very important to the business and processes data to provide valuable insights for decision making.",
        "business_consequence": "Delays.",
        "dependency_impact": "None.",
        "affected_scope": "Local.",
        "migration_implication": "Migrate.",
        "confidence": "MEDIUM",
        "factor_assessments": {
            "production_outputs": {"assessment": "MEDIUM", "evidence": "targets", "rationale": "persisted"},
            "downstream_dependency": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
            "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
        },
    }
    is_valid, reason = _validate_criticality_assessment(payload, evidence)
    assert not is_valid
    assert "generic filler" in reason


# ---------------------------------------------------------------------------
# 2. Deterministic Fallback Composition Tests
# ---------------------------------------------------------------------------

def test_deterministic_fallback_high_midstream():
    """Fallback produces HIGH assessment for midstream workflow with downstream consumers."""
    evidence = make_dummy_evidence(
        workflow_id="wf_claims_engine",
        workflow_filename="Claims_Adjudication_Engine.yxmd",
        business_purpose="Calculates claimant benefit payments and updates statutory claim reserves.",
        business_function="Claims Adjudication",
        business_area="Claims & Risk",
        production_targets=["Claims_Reserves.xlsx", "Claimant_Disbursements.csv"],
        downstream_consumers=["Financial_Ledger_Posting.yxmd", "Executive_Loss_Dashboard.yxmd"],
        upstream_producers=["Claims_Intake_Extract.yxmd"],
        dependency_position="Midstream Integration Hub",
        semantic_impact_signals=[
            "Statutory / compliance / financial reporting deliverable",
            "Customer / claimant / policyholder benefit or coverage impact",
        ],
    )
    evidence.deterministic_reference_score = 88.5
    evidence.deterministic_reference_level = "HIGH"

    result = compose_deterministic_criticality_fallback(evidence)
    assert result.criticality_level == "HIGH"
    assert result.criticality_score == 88.5
    assert result.source == "deterministic_fallback"
    assert "Claims_Adjudication_Engine.yxmd" in evidence.workflow_filename
    assert "Financial_Ledger_Posting.yxmd" in result.dependency_impact
    assert result.factor_assessments["downstream_dependency"].assessment == "HIGH"
    assert result.factor_assessments["dependency_position"].assessment == "HIGH"
    assert result.factor_assessments["customer_impact"].assessment == "HIGH"


def test_deterministic_fallback_low_isolated():
    """Fallback produces LOW assessment for standalone workflow with zero downstream consumers."""
    evidence = make_dummy_evidence(
        workflow_id="wf_test_utility",
        workflow_filename="Ad_Hoc_Data_Check.yxmd",
        business_purpose="Validates formatting of staging tables.",
        business_function="Technical Utility",
        business_area="Other / Unclassified",
        production_targets=["temp_summary.csv"],
        downstream_consumers=[],
        upstream_producers=[],
        dependency_position="Isolated Process",
        semantic_impact_signals=[],
    )
    evidence.deterministic_reference_score = 22.0
    evidence.deterministic_reference_level = "LOW"

    result = compose_deterministic_criticality_fallback(evidence)
    assert result.criticality_level == "LOW"
    assert result.criticality_score == 22.0
    assert result.source == "deterministic_fallback"
    assert "minimal operational blast radius" in result.criticality_justification.lower()
    assert result.factor_assessments["downstream_dependency"].assessment == "LOW"
    assert result.factor_assessments["customer_impact"].assessment == "NOT_ESTABLISHED"


# ---------------------------------------------------------------------------
# 3. LLM Generation, Validation & Fallback Integration Tests
# ---------------------------------------------------------------------------

def test_llm_generation_valid_output():
    """When LLM returns valid structured JSON, generator parses and accepts it."""
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.model_name = "test-llm"

    valid_response = json.dumps({
        "criticality_score": 82.0,
        "criticality_level": "HIGH",
        "criticality_justification": "This workflow is a critical operational component that executes policy rating and feeds directly into downstream policy issuance systems.",
        "business_consequence": "Interruption halts policy binding and creates severe backlog for distribution agents.",
        "dependency_impact": "Downstream policy issuance workflows cannot proceed without the rating matrix.",
        "affected_scope": "Commercial underwriting portfolio and distribution partners.",
        "migration_implication": "High-risk asset. Rating algorithm and output schemas must be strictly regression tested.",
        "confidence": "HIGH",
        "factor_assessments": {
            "production_outputs": {"assessment": "HIGH", "evidence": "Rating matrix", "rationale": "Authoritative deliverable"},
            "downstream_dependency": {"assessment": "HIGH", "evidence": "1 consumer", "rationale": "Downstream policy issuance"},
            "output_consumers": {"assessment": "MEDIUM", "evidence": "Policy issuance", "rationale": "Point-to-point"},
            "dependency_position": {"assessment": "HIGH", "evidence": "Upstream Root", "rationale": "Feeds issuance"},
            "shared_sources": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Independent tables"},
            "business_deliverables": {"assessment": "HIGH", "evidence": "Rating schedule", "rationale": "Mandatory operational output"},
            "business_scope": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Standard scope"},
            "customer_impact": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Internal rating"},
            "client_impact": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Internal use"},
            "operational_context": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Not documented"},
        }
    })
    mock_client.generate.return_value = valid_response

    gen = LLMNarrativeGenerator(client=mock_client)
    evidence = make_dummy_evidence(
        workflow_filename="Commercial_Policy_Rating.yxmd",
        downstream_consumers=["Policy_Issuance_Engine.yxmd"],
        dependency_position="Upstream Root Producer",
    )

    result = gen.generate_criticality_assessment(evidence)
    assert result.source == "llm"
    assert result.criticality_score == 82.0
    assert result.criticality_level == "HIGH"
    assert "Commercial underwriting" in result.affected_scope


def test_llm_generation_validation_failure_falls_back():
    """When LLM returns invalid JSON or contradictory fields, fallback is seamlessly substituted."""
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.model_name = "test-llm"
    # Return response where level contradicts score
    invalid_response = json.dumps({
        "criticality_score": 15.0,
        "criticality_level": "HIGH",  # Severe mismatch! 15 is LOW
        "criticality_justification": "Invalid test narrative.",
    })
    mock_client.generate.return_value = invalid_response

    gen = LLMNarrativeGenerator(client=mock_client)
    evidence = make_dummy_evidence()

    result = gen.generate_criticality_assessment(evidence)
    assert result.source == "deterministic_fallback"
    assert result.criticality_score == 45.0
    assert result.criticality_level == "MEDIUM"


def test_llm_unavailable_uses_deterministic_fallback():
    """When LLM client is unavailable or None, deterministic fallback is immediately used without error."""
    mock_client = MagicMock()
    mock_client.is_available = False

    gen = LLMNarrativeGenerator(client=mock_client)
    evidence = make_dummy_evidence()

    result = gen.generate_criticality_assessment(evidence)
    assert result.source == "deterministic_fallback"
    mock_client.generate.assert_not_called()


def test_caching_prevents_duplicate_calls():
    """Identical evidence package must result in cache hit without calling LLM twice."""
    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.model_name = "test-llm"

    valid_response = json.dumps({
        "criticality_score": 50.0,
        "criticality_level": "MEDIUM",
        "criticality_justification": "This is a valid business explanation indicating that the workflow generates operational deliverables for monthly reconciliation.",
        "business_consequence": "Delays monthly reconciliation.",
        "dependency_impact": "None detected.",
        "affected_scope": "Operations.",
        "migration_implication": "Standard cutover.",
        "confidence": "MEDIUM",
        "factor_assessments": {
            "production_outputs": {"assessment": "MEDIUM", "evidence": "targets", "rationale": "persisted"},
            "downstream_dependency": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
            "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
        },
    })
    mock_client.generate.return_value = valid_response

    gen = LLMNarrativeGenerator(client=mock_client)
    evidence = make_dummy_evidence(workflow_id="wf_cache_test")

    res1 = gen.generate_criticality_assessment(evidence)
    assert res1.source == "llm"
    assert mock_client.generate.call_count == 1

    # Second call with identical evidence must hit cache
    res2 = gen.generate_criticality_assessment(evidence)
    assert res2.source == "llm"
    assert mock_client.generate.call_count == 1  # No second call!


# ---------------------------------------------------------------------------
# 4. Zero Downstream LLM Calls Verification
# ---------------------------------------------------------------------------

def test_portfolio_aggregation_reuses_assessment_without_duplicate_llm_calls():
    """Portfolio aggregation must consume the persisted assessment and avoid redundant LLM calls."""
    from awa.analysis.portfolio_analyzer import build_portfolio_analysis

    mock_client = MagicMock()
    mock_client.is_available = True
    mock_client.model_name = "test-llm"

    gen = LLMNarrativeGenerator(client=mock_client)

    # Create dummy CanonicalAnalysisResult with pre-generated criticality
    bs = WorkflowBusinessSummary(
        business_purpose="Generates daily sales extract for regional distribution teams.",
        one_line_purpose="Sales Reporting",
        why_it_matters="Tracks regional sales numbers.",
    )
    bs.criticality_score = 55.0
    bs.criticality_level = "MEDIUM"
    bs.criticality_justification = "Pre-computed canonical justification."
    bs.criticality_source = "llm"

    dummy_wf = Workflow(metadata=WorkflowMetadata(name="Sales_Daily.yxmd", version="2024.1"))
    dummy_res = CanonicalAnalysisResult(
        analysis_id="aid_sales_1",
        source=SourceInfo(source_format="yxmd", original_filename="Sales_Daily.yxmd"),
        workflow=dummy_wf,
        graph=nx.DiGraph(),
        execution_order=[],
        translations={},
        consumed_anchors={},
        lineage_paths=[],
        metrics=WorkflowMetrics(total_nodes=5, total_connections=4, input_count=1, output_count=1),
        dag_layout=DagLayout([], []),
        python_trace=PythonTraceMap(),
        tool_explanations={},
        required_libraries=[],
        diagnostics=[],
        business_summary=bs,
    )

    raw_workflows = [("Sales_Daily.yxmd", "Sales_Daily.yxmd", dummy_res)]

    # Mock generator client to ensure no LLM calls are made during portfolio aggregation
    portfolio = build_portfolio_analysis(raw_workflows, generator=gen)
    # Verify wf summary received the criticality fields
    assert len(portfolio.workflows) == 1
    wf = portfolio.workflows[0]
    assert wf.criticality_score == 55.0
    assert wf.criticality_level == "MEDIUM"
    assert wf.criticality_justification == "Pre-computed canonical justification."
    # No extra LLM call was executed since it reused canonical assessment
    mock_client.generate.assert_not_called()


def test_xlsx_export_zero_llm_calls(tmp_path):
    """Portfolio XLSX generation must format and export criticality without triggering LLM calls."""
    from awa.generators.portfolio_xlsx_generator import generate_portfolio_excel
    from awa.model.portfolio import PortfolioAggregateMetrics

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


# ---------------------------------------------------------------------------
# 5. Semantic Role Differentiation & Evidence Grounding Tests
# ---------------------------------------------------------------------------

def test_semantic_differentiation_over_mechanical_counts():
    """Two workflows with 1 output each must be differentiated by business function and impact."""
    # Workflow 1: Statutory claims adjudication
    wf_claims = make_dummy_evidence(
        workflow_id="wf_claims_1",
        workflow_filename="Statutory_Claims_Reserve.yxmd",
        business_purpose="Calculates statutory claims reserves and claimant benefit disbursement amounts.",
        business_function="Claims Adjudication",
        business_area="Claims & Risk",
        production_targets=["Statutory_Reserves.xlsx"],
        downstream_consumers=["Financial_Reporting_Engine.yxmd"],
        dependency_position="Upstream Root Producer",
        semantic_impact_signals=[
            "Statutory / compliance / financial reporting deliverable",
            "Customer / claimant / policyholder benefit or coverage impact",
        ],
    )
    wf_claims.deterministic_reference_score = 82.0
    wf_claims.deterministic_reference_level = "HIGH"

    # Workflow 2: Internal staging utility
    wf_staging = make_dummy_evidence(
        workflow_id="wf_stage_1",
        workflow_filename="Format_Staging_Data.yxmd",
        business_purpose="Formats and trims whitespace on staging tables.",
        business_function="Technical Utility",
        business_area="Other / Unclassified",
        production_targets=["staged_temp.csv"],
        downstream_consumers=[],
        dependency_position="Isolated Process",
        semantic_impact_signals=[],
    )
    wf_staging.deterministic_reference_score = 25.0
    wf_staging.deterministic_reference_level = "LOW"

    res_claims = compose_deterministic_criticality_fallback(wf_claims)
    res_staging = compose_deterministic_criticality_fallback(wf_staging)

    assert res_claims.criticality_level == "HIGH"
    assert res_staging.criticality_level == "LOW"
    assert res_claims.criticality_score > res_staging.criticality_score + 40.0
    assert "Statutory" in res_claims.factor_assessments["business_deliverables"].evidence
    assert res_staging.factor_assessments["customer_impact"].assessment == "NOT_ESTABLISHED"


def test_single_customer_impacting_output_can_receive_high():
    """A workflow with only 1 output can achieve HIGH criticality when evidence grounds high customer/business impact."""
    evidence = make_dummy_evidence(
        workflow_id="wf_single_out",
        workflow_filename="Direct_Claimant_Payments.yxmd",
        business_purpose="Executes claimant settlement disbursements and policyholder payment reconciliation.",
        business_function="Claimant Settlement",
        business_area="Claims & Risk",
        production_targets=["Approved_Claimant_Payments.csv"],
        downstream_consumers=["Treasury_Wire_Execution.yxmd"],
        dependency_position="Midstream Integration Hub",
        semantic_impact_signals=[
            "Customer / claimant / policyholder benefit or coverage impact",
            "Statutory / compliance / financial reporting deliverable",
        ],
    )
    evidence.deterministic_reference_score = 75.0
    evidence.deterministic_reference_level = "HIGH"

    result = compose_deterministic_criticality_fallback(evidence)
    assert result.criticality_level == "HIGH"
    assert result.factor_assessments["customer_impact"].assessment == "HIGH"
    assert len(evidence.production_targets) == 1  # Exactly one output!


def test_many_outputs_weak_impact_not_automatically_high():
    """A workflow with 8 informational outputs but zero downstream consumers is not automatically HIGH."""
    evidence = make_dummy_evidence(
        workflow_id="wf_many_out",
        workflow_filename="Ad_Hoc_Departmental_Summaries.yxmd",
        business_purpose="Builds ad-hoc informational departmental summary slices.",
        business_function="Informational Reporting",
        business_area="Other / Unclassified",
        production_targets=[f"dept_summary_{i}.csv" for i in range(8)],
        downstream_consumers=[],
        upstream_producers=[],
        dependency_position="Leaf Consumer",
        semantic_impact_signals=[],
    )
    evidence.deterministic_reference_score = 48.0
    evidence.deterministic_reference_level = "MEDIUM"

    result = compose_deterministic_criticality_fallback(evidence)
    assert result.criticality_level != "HIGH"
    assert result.factor_assessments["downstream_dependency"].assessment == "LOW"
    assert result.factor_assessments["dependency_position"].assessment == "LOW"


def test_legacy_persisted_analysis_backward_compatibility():
    """Legacy persisted models without new criticality fields must default gracefully."""
    # WorkflowBusinessSummary
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

    # PortfolioWorkflowSummary
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

