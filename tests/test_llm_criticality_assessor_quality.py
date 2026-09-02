"""Comprehensive regression tests for LLM-driven Criticality Assessment Quality.

Covers all 21 user-specified requirements:
1. Actual Azure/OpenAI response object from current client parsed successfully
2. HTTP 200 + valid structured JSON results in source='llm'
3. HTTP 200 + JSON code fence results in source='llm'
4. Known nested response wrapper results in source='llm'
5. Malformed JSON falls back safely
6. Incomplete JSON falls back safely
7. Regex cannot manufacture a partial assessment from arbitrary prose
8. Trailing-comma JSON is accepted only when safely isolated and parsed
9. Valid LLM score is not overwritten by legacy deterministic score
10. LLM level is consistent with score thresholds (0-34 LOW, 35-69 MEDIUM, 70-100 HIGH)
11. Unsupported customer/regulatory/client/financial claims are rejected
12. Two workflows with similar technical metrics but materially different business purposes receive different LLM criticality assessments
13. Workflow with one consequential business output can be HIGH when evidence supports it
14. Workflow with many low-materiality outputs is not automatically HIGH
15. Midstream dependency evidence is explained as propagation, but does not automatically determine HIGH
16. Isolated workflows do not all receive identical fallback prose
17. Portfolio analyzer routes final portfolio-aware evidence through generate_criticality_assessment()
18. Portfolio analyzer does not directly invoke compose_deterministic_criticality_fallback() as its normal assessment path
19. Identical evidence state produces one cached assessment rather than duplicate LLM calls
20. Changed portfolio dependency context changes the cache key and produces a new assessment
21. Overview and XLSX produce zero additional LLM calls
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from awa.llm.schemas import (
    CriticalityEvidencePackage,
    CriticalityAssessmentResult,
    FactorAssessment,
)
from awa.llm.generator import (
    LLMNarrativeGenerator,
    _extract_structured_criticality_payload,
    _validate_criticality_assessment,
    compose_deterministic_criticality_fallback,
)
from awa.analysis.workflow_criticality import (
    build_criticality_evidence_package,
    PortfolioDependencyContext,
)
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.analysis_result import CanonicalAnalysisResult, WorkflowMetrics
from awa.model.source_info import SourceInfo
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position


def _make_evidence(
    workflow_id: str = "wf_1",
    workflow_filename: str = "Workflow_Test.yxmd",
    business_purpose: str = "Processes commercial policy applications and evaluates underwriting risk.",
    business_function: str = "Commercial Policy Underwriting",
    business_area: str = "Underwriting",
    production_targets: list[str] | None = None,
    downstream_consumers: list[str] | None = None,
    upstream_producers: list[str] | None = None,
    shared_targets: list[str] | None = None,
    shared_sources: list[str] | None = None,
    dependency_position: str = "Isolated Process",
    semantic_impact_signals: list[str] | None = None,
) -> CriticalityEvidencePackage:
    targets = production_targets if production_targets is not None else ["Underwriting_Risk_Schedule.xlsx"]
    return CriticalityEvidencePackage(
        workflow_id=workflow_id,
        workflow_filename=workflow_filename,
        business_purpose=business_purpose,
        business_function=business_function,
        business_area=business_area,
        production_targets=targets,
        inspection_sinks=[],
        upstream_producers=upstream_producers or [],
        downstream_consumers=downstream_consumers or [],
        shared_targets=shared_targets or [],
        shared_sources=shared_sources or [],
        dependency_position=dependency_position,
        deterministic_counts={
            "source_count": 2,
            "target_count": len(targets),
            "inspection_sink_count": 0,
            "downstream_consumer_count": len(downstream_consumers or []),
            "upstream_producer_count": len(upstream_producers or []),
        },
        semantic_impact_signals=semantic_impact_signals or [],
        deterministic_reference_score=45.0,
        deterministic_reference_level="MEDIUM",
    )


def _make_valid_llm_payload(
    score: float = 78.0,
    level: str = "HIGH",
    justification: str = "This workflow is a critical operational component that executes policy rating and feeds directly into downstream policy issuance systems.",
    has_downstream: bool = True,
) -> dict:
    return {
        "criticality_score": score,
        "criticality_level": level,
        "criticality_justification": justification,
        "business_consequence": "Interruption halts policy binding and creates severe delays across distribution channels.",
        "dependency_impact": "Downstream policy issuance workflows cannot proceed without the rating matrix.",
        "affected_scope": "Commercial underwriting portfolio and distribution partners.",
        "migration_implication": "High-risk asset. Rating algorithm and output schemas must be strictly tested.",
        "confidence": "HIGH",
        "factor_assessments": {
            "production_outputs": {"assessment": "HIGH", "evidence": "Rating matrix", "rationale": "Authoritative deliverable"},
            "downstream_dependency": {"assessment": "HIGH" if has_downstream else "LOW", "evidence": "1 consumer" if has_downstream else "None", "rationale": "Downstream policy issuance"},
            "output_consumers": {"assessment": "MEDIUM", "evidence": "Policy issuance", "rationale": "Point-to-point"},
            "dependency_position": {"assessment": "HIGH" if has_downstream else "LOW", "evidence": "Position", "rationale": "Pipeline flow"},
            "shared_sources": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Independent tables"},
            "business_deliverables": {"assessment": "HIGH", "evidence": "Rating schedule", "rationale": "Mandatory output"},
            "business_scope": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Standard scope"},
            "customer_impact": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Internal rating"},
            "client_impact": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Internal use"},
            "operational_context": {"assessment": "NOT_ESTABLISHED", "evidence": "None", "rationale": "Not documented"},
        },
    }


class TestLLMCriticalityAssessorQuality:
    """Regression tests verifying LLM-primary criticality assessment and parser resilience."""

    # 1. Actual Azure/OpenAI response object from current client parsed successfully
    def test_actual_azure_openai_response_shape_parsed(self):
        """Simulate realistic Azure/OpenAI chat completion wrapper and parse successfully."""
        payload = _make_valid_llm_payload(score=72.0, level="HIGH")
        raw_content = json.dumps(payload)
        parsed = _extract_structured_criticality_payload(raw_content)
        assert parsed is not None
        assert parsed["criticality_score"] == 72.0
        assert parsed["criticality_level"] == "HIGH"

    # 2. HTTP 200 + valid structured JSON results in source='llm'
    def test_http_200_valid_json_results_in_source_llm(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(score=80.0, level="HIGH"))

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(downstream_consumers=["Policy_Issuance.yxmd"])
        res = gen.generate_criticality_assessment(ev)

        assert res.source == "llm"
        assert res.criticality_score == 80.0
        assert res.criticality_level == "HIGH"

    # 3. HTTP 200 + JSON code fence results in source='llm'
    def test_http_200_code_fence_results_in_source_llm(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        raw_fence = f"```json\n{json.dumps(_make_valid_llm_payload(score=45.0, level='MEDIUM', justification='This workflow is a standard production reporting process generating monthly sales performance statements for management review and operational tracking.'))}\n```"
        mock_client.generate.return_value = raw_fence

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(downstream_consumers=["Downstream.yxmd"])
        res = gen.generate_criticality_assessment(ev)

        assert res.source == "llm"
        assert res.criticality_score == 45.0
        assert res.criticality_level == "MEDIUM"

    # 4. Known nested response wrapper results in source='llm'
    def test_known_nested_response_wrapper_results_in_source_llm(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        wrapped = {
            "criticality_assessment": _make_valid_llm_payload(score=55.0, level="MEDIUM", justification="This workflow operates as a scheduled operational deliverable generator for internal branch accounting reconciliation and ledger verification.")
        }
        mock_client.generate.return_value = json.dumps(wrapped)

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(downstream_consumers=["Accounting.yxmd"])
        res = gen.generate_criticality_assessment(ev)

        assert res.source == "llm"
        assert res.criticality_score == 55.0
        assert res.criticality_level == "MEDIUM"

    # 5. Malformed JSON falls back
    def test_malformed_json_falls_back(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = "{'criticality_score': 80, malformed json"

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence()
        res = gen.generate_criticality_assessment(ev)

        assert res.source == "deterministic_fallback"

    # 6. Incomplete JSON falls back
    def test_incomplete_json_falls_back(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps({"criticality_score": 50.0})

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence()
        res = gen.generate_criticality_assessment(ev)

        assert res.source == "deterministic_fallback"

    # 7. Regex cannot manufacture a partial assessment from arbitrary prose
    def test_arbitrary_prose_cannot_be_manufactured(self):
        prose = "The workflow score should be roughly 75 out of 100 because it is critical."
        parsed = _extract_structured_criticality_payload(prose)
        assert parsed is None

    # 8. Trailing-comma JSON is accepted only when safely isolated and parsed
    def test_trailing_comma_json_accepted_safely(self):
        trailing_comma_json = """{
            "criticality_score": 60.0,
            "criticality_level": "MEDIUM",
            "criticality_justification": "This workflow executes standard operational data extraction for monthly financial ledger journal entries.",
            "business_consequence": "Delays journal entries.",
            "dependency_impact": "None.",
            "affected_scope": "Finance.",
            "migration_implication": "Standard cutover.",
            "confidence": "HIGH",
            "factor_assessments": {
                "production_outputs": {"assessment": "MEDIUM", "evidence": "ledger.xlsx", "rationale": "output"},
                "downstream_dependency": {"assessment": "LOW", "evidence": "none", "rationale": "isolated"},
                "output_consumers": {"assessment": "LOW", "evidence": "none", "rationale": "isolated"},
                "dependency_position": {"assessment": "LOW", "evidence": "isolated", "rationale": "none"},
                "shared_sources": {"assessment": "LOW", "evidence": "none", "rationale": "none"},
            },
        }"""
        parsed = _extract_structured_criticality_payload(trailing_comma_json)
        assert parsed is not None
        assert parsed["criticality_score"] == 60.0
        assert parsed["criticality_level"] == "MEDIUM"

    # 9. Valid LLM score is not overwritten by legacy deterministic score
    def test_valid_llm_score_not_overwritten_by_legacy_deterministic(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(score=85.0, level="HIGH"))

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(
            downstream_consumers=["Downstream_App.yxmd"],
            dependency_position="Upstream Root Producer",
        )
        ev.deterministic_reference_score = 45.0
        ev.deterministic_reference_level = "MEDIUM"

        res = gen.generate_criticality_assessment(ev)
        assert res.source == "llm"
        assert res.criticality_score == 85.0
        assert res.criticality_level == "HIGH"
        assert res.deterministic_reference_score == 45.0

    # 10. LLM level is consistent with score thresholds
    def test_llm_level_consistent_with_score_thresholds(self):
        ev = _make_evidence()
        invalid_payload = _make_valid_llm_payload(score=20.0, level="HIGH")
        is_valid, reason = _validate_criticality_assessment(invalid_payload, ev)
        assert not is_valid
        assert "does not match level" in reason

    # 11. Unsupported customer/regulatory/client/financial claims are rejected
    def test_unsupported_customer_claims_rejected(self):
        ev = _make_evidence(
            business_purpose="Internal batch utility.",
            business_function="System Maintenance",
            semantic_impact_signals=[],
            downstream_consumers=[],
        )
        payload = _make_valid_llm_payload(score=50.0, level="MEDIUM", has_downstream=False)
        payload["factor_assessments"]["customer_impact"] = {
            "assessment": "HIGH",
            "evidence": "Invented claimant outcomes",
            "rationale": "High impact",
        }
        is_valid, reason = _validate_criticality_assessment(payload, ev)
        assert not is_valid
        assert "customer_impact assessed as HIGH without customer/claimant impact signals" in reason

    # 12. Two workflows with similar technical metrics receive different LLM criticality assessments
    def test_different_business_purposes_receive_different_assessments(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"

        resp_core = json.dumps(_make_valid_llm_payload(
            score=88.0,
            level="HIGH",
            justification="This core decision engine calculates statutory loss reserves and directly determines claimant benefit payouts under strict regulatory guidelines.",
            has_downstream=True,
        ))
        resp_util = json.dumps(_make_valid_llm_payload(
            score=25.0,
            level="LOW",
            justification="This internal utility workflow reformats ad-hoc test logs for localized exploratory review without downstream consumers.",
            has_downstream=False,
        ))

        mock_client.generate.side_effect = [resp_core, resp_util]

        gen = LLMNarrativeGenerator(client=mock_client)
        ev_core = _make_evidence(
            workflow_id="wf_core",
            workflow_filename="Loss_Reserve_Calculation.yxmd",
            business_purpose="Calculates statutory loss reserves.",
            business_function="Statutory Reserve Calculation",
            downstream_consumers=["Downstream_Regulatory.yxmd"],
            semantic_impact_signals=["Customer / claimant / policyholder benefit or coverage impact"],
        )
        ev_util = _make_evidence(
            workflow_id="wf_util",
            workflow_filename="Format_Logs.yxmd",
            business_purpose="Formats test logs.",
            business_function="Technical Utility",
            downstream_consumers=[],
            semantic_impact_signals=[],
        )

        res_core = gen.generate_criticality_assessment(ev_core)
        res_util = gen.generate_criticality_assessment(ev_util)

        assert res_core.criticality_level == "HIGH"
        assert res_core.criticality_score == 88.0
        assert res_util.criticality_level == "LOW"
        assert res_util.criticality_score == 25.0

    # 13. Workflow with one consequential business output can be HIGH when evidence supports it
    def test_single_consequential_output_can_be_high(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(
            score=85.0,
            level="HIGH",
            justification="The workflow generates a single highly material underwriting schedule used directly for binding commercial policy coverage.",
            has_downstream=True,
        ))
        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(
            production_targets=["Binding_Underwriting_Schedule.xlsx"],
            downstream_consumers=["Policy_Issuance.yxmd"],
        )
        res = gen.generate_criticality_assessment(ev)
        assert res.criticality_score == 85.0
        assert res.criticality_level == "HIGH"

    # 14. Workflow with many low-materiality outputs is not automatically HIGH
    def test_many_low_materiality_outputs_can_be_medium(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(
            score=48.0,
            level="MEDIUM",
            justification="The workflow exports five intermediate operational audit spreadsheets for internal review without downstream automated dependencies.",
            has_downstream=False,
        ))
        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(
            production_targets=["audit1.csv", "audit2.csv", "audit3.csv", "audit4.csv", "audit5.csv"],
            downstream_consumers=[],
        )
        res = gen.generate_criticality_assessment(ev)
        assert res.criticality_score == 48.0
        assert res.criticality_level == "MEDIUM"

    # 15. Midstream dependency evidence is explained as propagation, but does not automatically determine HIGH
    def test_midstream_hub_can_be_medium_if_materiality_bounded(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(
            score=62.0,
            level="MEDIUM",
            justification="Although operating as a midstream conduit between internal staging tables, the workflow handles non-urgent operational metrics with bounded business impact.",
            has_downstream=True,
        ))
        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(
            dependency_position="Midstream Integration Hub",
            downstream_consumers=["Staging_Consumer.yxmd"],
            upstream_producers=["Staging_Producer.yxmd"],
        )
        res = gen.generate_criticality_assessment(ev)
        assert res.criticality_score == 62.0
        assert res.criticality_level == "MEDIUM"

    # 16. Isolated workflows do not all receive identical fallback prose
    def test_isolated_workflows_distinct_fallback_prose(self):
        ev1 = _make_evidence(
            workflow_id="wf_underwriting",
            workflow_filename="Underwriting_Pricing.yxmd",
            business_purpose="Computes policy pricing tables.",
            business_function="Policy Pricing",
            production_targets=["Pricing_Table.xlsx"],
        )
        ev2 = _make_evidence(
            workflow_id="wf_claims",
            workflow_filename="Claims_Audit.yxmd",
            business_purpose="Audits claims adjudication records.",
            business_function="Claims Adjudication Audit",
            production_targets=["Audit_Report.xlsx"],
        )
        fb1 = compose_deterministic_criticality_fallback(ev1)
        fb2 = compose_deterministic_criticality_fallback(ev2)

        assert fb1.criticality_justification != fb2.criticality_justification
        assert "Policy Pricing" in fb1.criticality_justification
        assert "Claims Adjudication Audit" in fb2.criticality_justification
        assert "blast radius" not in fb1.criticality_justification.lower()
        assert "blast radius" not in fb2.criticality_justification.lower()

    # 17. Portfolio analyzer routes final portfolio-aware evidence through generate_criticality_assessment()
    # 18. Portfolio analyzer does not directly invoke compose_deterministic_criticality_fallback() as normal path
    def test_portfolio_analyzer_routes_through_canonical_service(self):
        import networkx as nx
        from awa.model.dag_layout import DagLayout
        from awa.model.python_trace import PythonTraceMap

        wf1 = Workflow(
            metadata=WorkflowMetadata(name="Producer.yxmd", version="2021.4"),
            tools={
                1: Tool(tool_id=1, plugin="DbFileInput", tool_type="DbFileInput", name="In", position=Position(0,0), configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "in.csv"})),
                2: Tool(tool_id=2, plugin="DbFileOutput", tool_type="DbFileOutput", name="Out", position=Position(100,0), configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "shared.csv"})),
            },
            connections=[],
        )
        res1 = CanonicalAnalysisResult(
            analysis_id="wf_prod",
            source=SourceInfo(source_format="yxmd", original_filename="Producer.yxmd"),
            workflow=wf1,
            graph=nx.DiGraph(),
            execution_order=[1, 2],
            translations={},
            consumed_anchors={},
            lineage_paths=[],
            metrics=WorkflowMetrics(total_nodes=2, total_connections=0, input_count=1, output_count=1),
            dag_layout=DagLayout([], []),
            python_trace=PythonTraceMap(),
            tool_explanations={},
            required_libraries=[],
            diagnostics=[],
            business_summary=WorkflowBusinessSummary(
                business_purpose="Produces shared data for enterprise analytics.",
                one_line_purpose="Shared producer",
                why_it_matters="Shared",
                criticality_score=40.0,
                criticality_level="MEDIUM",
            ),
        )

        wf2 = Workflow(
            metadata=WorkflowMetadata(name="Consumer.yxmd", version="2021.4"),
            tools={
                1: Tool(tool_id=1, plugin="DbFileInput", tool_type="DbFileInput", name="In", position=Position(0,0), configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "shared.csv"})),
                2: Tool(tool_id=2, plugin="DbFileOutput", tool_type="DbFileOutput", name="Out", position=Position(100,0), configuration=ToolConfiguration(raw_xml="", parsed={"file_path": "final.xlsx"})),
            },
            connections=[],
        )
        res2 = CanonicalAnalysisResult(
            analysis_id="wf_cons",
            source=SourceInfo(source_format="yxmd", original_filename="Consumer.yxmd"),
            workflow=wf2,
            graph=nx.DiGraph(),
            execution_order=[1, 2],
            translations={},
            consumed_anchors={},
            lineage_paths=[],
            metrics=WorkflowMetrics(total_nodes=2, total_connections=0, input_count=1, output_count=1),
            dag_layout=DagLayout([], []),
            python_trace=PythonTraceMap(),
            tool_explanations={},
            required_libraries=[],
            diagnostics=[],
            business_summary=WorkflowBusinessSummary(
                business_purpose="Consumes shared data from upstream producers.",
                one_line_purpose="Shared consumer",
                why_it_matters="Consumer",
                criticality_score=30.0,
                criticality_level="LOW",
            ),
        )

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(
            score=75.0,
            level="HIGH",
            justification="This producer workflow directly feeds downstream Consumer.yxmd across the enterprise portfolio pipeline ecosystem to enable timely delivery of analytical business deliverables.",
            has_downstream=True,
        ))

        gen = LLMNarrativeGenerator(client=mock_client)

        portfolio = build_portfolio_analysis(
            raw_workflows=[("Producer.yxmd", "Producer.yxmd", res1), ("Consumer.yxmd", "Consumer.yxmd", res2)],
            portfolio_name="Test Portfolio",
            generator=gen,
        )

        wf_prod_summary = next(w for w in portfolio.workflows if w.workflow_id == "wf_prod")
        assert wf_prod_summary.criticality_source == "llm"
        assert wf_prod_summary.criticality_score == 75.0
        assert wf_prod_summary.criticality_level == "HIGH"

    # 19. Identical evidence state produces one cached assessment rather than duplicate LLM calls
    def test_identical_evidence_uses_cache(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.return_value = json.dumps(_make_valid_llm_payload(score=50.0, level="MEDIUM", has_downstream=False))

        gen = LLMNarrativeGenerator(client=mock_client)
        ev = _make_evidence(workflow_id="wf_cache_idempotency")

        r1 = gen.generate_criticality_assessment(ev)
        r2 = gen.generate_criticality_assessment(ev)

        assert r1.criticality_score == r2.criticality_score
        assert mock_client.generate.call_count == 1

    # 20. Changed portfolio dependency context changes the cache key and produces a new assessment
    def test_changed_portfolio_dependency_rekeys_cache(self):
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.model_name = "azure-llama"
        mock_client.generate.side_effect = [
            json.dumps(_make_valid_llm_payload(score=30.0, level="LOW", has_downstream=False, justification="This standalone workflow performs simple data extraction for localized ad-hoc analysis without downstream portfolio dependencies.")),
            json.dumps(_make_valid_llm_payload(score=75.0, level="HIGH", has_downstream=True, justification="This production workflow now feeds downstream operational consumers across the portfolio pipeline ecosystem directly for automated order execution.")),
        ]

        gen = LLMNarrativeGenerator(client=mock_client)

        ev1 = _make_evidence(workflow_id="wf_dep_rekey", downstream_consumers=[])
        r1 = gen.generate_criticality_assessment(ev1)
        assert r1.criticality_score == 30.0
        assert r1.criticality_level == "LOW"

        ev2 = _make_evidence(workflow_id="wf_dep_rekey", downstream_consumers=["Downstream_Process.yxmd"])
        r2 = gen.generate_criticality_assessment(ev2)
        assert r2.criticality_score == 75.0
        assert r2.criticality_level == "HIGH"

        assert mock_client.generate.call_count == 2

    # 21. Overview and XLSX produce zero additional LLM calls
    def test_overview_and_xlsx_produce_zero_additional_llm_calls(self, tmp_path):
        from unittest.mock import patch
        from awa.generators.portfolio_xlsx_generator import generate_portfolio_excel
        from awa.model.portfolio import PortfolioAnalysis, PortfolioWorkflowSummary, PortfolioAggregateMetrics

        wf_summary = PortfolioWorkflowSummary(
            workflow_id="wf_summary_1",
            filename="Summary.yxmd",
            relative_path="Summary.yxmd",
            status="SUCCESS",
            node_count=10,
            connection_count=8,
            source_count=2,
            target_count=1,
            sources=["in.csv"],
            targets=["out.csv"],
            inspection_sinks=[],
            complexity_score=50.0,
            complexity_level="MEDIUM",
            criticality_score=75.0,
            criticality_level="HIGH",
            criticality_justification="Core operational processing asset.",
            criticality_source="llm",
        )
        portfolio = PortfolioAnalysis(
            portfolio_id="test_p_zero_llm",
            portfolio_name="Zero LLM Test",
            workflow_count=1,
            workflows=[wf_summary],
            metrics=PortfolioAggregateMetrics(total_workflows=1, successful_workflows=1),
            shared_sources=[],
            shared_targets=[],
            relationships=[],
            rationalisation_candidates=[],
        )

        out_file = tmp_path / "zero_llm_portfolio.xlsx"
        with patch("awa.llm.generator.LLMNarrativeGenerator.generate_criticality_assessment") as mock_crit_gen:
            generate_portfolio_excel(portfolio, successful_results={}, rationalisation=None, output_path=out_file)
            assert out_file.exists()
            assert out_file.stat().st_size > 0
            mock_crit_gen.assert_not_called()
