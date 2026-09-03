"""Tests for Actuarial Business Area Integration, 5-Area Segregation, and Deterministic Operational Data in Portfolio."""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from awa.analysis.business_area_classifier import (
    classify_workflow_business_area,
    classify_business_area_deterministic,
    classify_business_function_deterministic,
    compose_deterministic_business_purpose,
)
from awa.analysis.business_area_definitions import (
    ALLOWED_BUSINESS_AREAS,
    BUSINESS_AREA_DEFINITIONS,
)
from awa.analysis.portfolio_analyzer import (
    build_portfolio_analysis,
    CONFIGURED_PORTFOLIO_BUSINESS_AREAS,
)
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.business_summary import WorkflowBusinessSummary
from awa.model.tool import Tool, ToolConfiguration
from app.models.schemas import PortfolioWorkflowSummaryDTO


def _make_dummy_canonical(
    analysis_id: str,
    filename: str,
    business_purpose: str = "",
    target_files: list[str] | None = None,
    output_columns: list[str] | None = None,
    source_files: list[str] | None = None,
) -> CanonicalAnalysisResult:
    res = MagicMock(spec=CanonicalAnalysisResult)
    res.analysis_id = analysis_id

    res.source = MagicMock()
    res.source.original_filename = filename

    res.workflow = MagicMock()
    res.workflow.metadata = MagicMock()
    res.workflow.metadata.name = filename
    res.workflow.connections = []
    res.workflow.tools = {}

    res.execution_order = []
    res.graph = MagicMock()
    res.graph.has_node = MagicMock(return_value=True)
    res.graph.out_degree = MagicMock(return_value=0)
    res.graph.predecessors = MagicMock(return_value=[])
    res.graph.number_of_nodes = MagicMock(return_value=1)
    res.graph.number_of_edges = MagicMock(return_value=0)
    res.graph.nodes = ["1"]
    res.graph.edges = []

    target_files = target_files or []
    output_columns = output_columns or []
    source_files = source_files or []

    for idx, src in enumerate(source_files, 1):
        tid = f"src_{idx}"
        res.execution_order.append(tid)
        tool = MagicMock(spec=Tool)
        tool.tool_type = "DbFileInput"
        tool.configuration = MagicMock(spec=ToolConfiguration)
        tool.configuration.parsed = {"file_path": src}
        tool.output_fields = []
        res.workflow.tools[tid] = tool

    for idx, tgt in enumerate(target_files, 1):
        tid = f"tgt_{idx}"
        res.execution_order.append(tid)
        tool = MagicMock(spec=Tool)
        tool.tool_type = "DbFileOutput"
        tool.configuration = MagicMock(spec=ToolConfiguration)
        tool.configuration.parsed = {"file_path": tgt}
        mock_fields = []
        for col in output_columns:
            f = MagicMock()
            f.name = col
            mock_fields.append(f)
        tool.output_fields = mock_fields
        res.workflow.tools[tid] = tool

    bs = MagicMock(spec=WorkflowBusinessSummary)
    bs.business_purpose = business_purpose
    bs.business_outputs = []
    bs.source_inputs = []
    res.business_summary = bs

    res.metrics = MagicMock()
    res.metrics.total_connections = 0
    res.sttm = None
    return res


class TestActuarialClassification:
    """Test Actuarial domain taxonomy and classification rules."""

    def test_authoritative_taxonomy_contains_actuarial(self):
        """Actuarial is part of authoritative taxonomy and allowed business areas."""
        assert "Actuarial" in ALLOWED_BUSINESS_AREAS
        assert "Actuarial" in BUSINESS_AREA_DEFINITIONS
        assert "Actuarial" in CONFIGURED_PORTFOLIO_BUSINESS_AREAS

        actuarial_def = BUSINESS_AREA_DEFINITIONS["Actuarial"]
        assert actuarial_def.name == "Actuarial"
        assert any("reserving" in act.lower() or "triangulation" in act.lower() for act in actuarial_def.included_activities)

    def test_actuarial_classification_loss_reserving(self):
        """Workflow performing loss development triangulation and IBNR estimation classifies as Actuarial."""
        wf = _make_dummy_canonical(
            "act_1",
            "Loss_Development_Triangles.yxmd",
            business_purpose="Generates chain ladder loss triangles and estimates IBNR reserves for casualty lines.",
            target_files=["Casualty_IBNR_Reserves.xlsx"],
            output_columns=["Accident_Year", "Development_Lag", "Cumulative_Losses", "IBNR_Reserve"],
        )
        res = classify_workflow_business_area(result=wf)
        assert res.business_area == "Actuarial"
        func = classify_business_function_deterministic(business_area="Actuarial", business_purpose=wf.business_summary.business_purpose)
        assert "Actuarial" in func or "Reserve" in func or "Valuation" in func

    def test_actuarial_classification_rate_indications(self):
        """Workflow computing actuarial rate indications classifies as Actuarial."""
        wf = _make_dummy_canonical(
            "act_2",
            "Auto_Rate_Indication_Model.yxmd",
            business_purpose="Calculates actuarial indicated rate changes and loss trend selections.",
            target_files=["Rate_Filing_Indications.xlsx"],
            output_columns=["Coverage_Type", "Indicated_Rate_Change", "Permissible_Loss_Ratio"],
        )
        res = classify_workflow_business_area(result=wf)
        assert res.business_area == "Actuarial"

    def test_actuarial_classification_solvency_capital(self):
        """Workflow computing solvency capital modeling classifies as Actuarial."""
        wf = _make_dummy_canonical(
            "act_3",
            "Solvency_II_Capital_Requirement.yxmd",
            business_purpose="Performs solvency II capital modeling and asset liability matching risk margin calculation.",
            target_files=["SCR_Risk_Margin.xlsx"],
            output_columns=["Solvency_Capital_Requirement", "Risk_Margin", "Best_Estimate_Liability"],
        )
        res = classify_workflow_business_area(result=wf)
        assert res.business_area == "Actuarial"

    def test_generic_insurance_not_classified_as_actuarial(self):
        """General claims workflow without actuarial indicators remains Claims & Risk."""
        wf = _make_dummy_canonical(
            "claim_1",
            "Monthly_Claims_Paid_Extract.yxmd",
            business_purpose="Extracts monthly paid indemnity and medical claim disbursements.",
            target_files=["Claims_Paid.xlsx"],
            output_columns=["Claim_ID", "Paid_Loss", "Payment_Date"],
        )
        res = classify_workflow_business_area(result=wf)
        assert res.business_area == "Claims & Risk"
        assert res.business_area != "Actuarial"

    def test_underwriting_policy_not_classified_as_actuarial(self):
        """Underwriting eligibility and premium scoring workflow remains Underwriting."""
        wf = _make_dummy_canonical(
            "uw_1",
            "Commercial_Policy_Underwriting.yxmd",
            business_purpose="Evaluates applicant risk scores and determines policy underwriting acceptance.",
            target_files=["Underwriting_Decisions.xlsx"],
            output_columns=["Policy_Number", "Underwriting_Tier", "Base_Premium"],
        )
        res = classify_workflow_business_area(result=wf)
        assert res.business_area == "Underwriting"
        assert res.business_area != "Actuarial"


class TestPortfolioSegregationAndOperationalData:
    """Test 5-area portfolio segregation, count integrity, and operational factor values."""

    def test_portfolio_5_business_areas_and_operational_fields(self):
        """Portfolio materializes exactly the 5 configured business areas and includes last_run/frequency."""
        wf_claims = _make_dummy_canonical(
            "wf_1", "Claims.yxmd",
            business_purpose="Processes insurance claim losses and claimant exposure.",
            target_files=["Claims_Loss.xlsx"], output_columns=["Claim_ID", "Loss_Amount"]
        )
        wf_legal = _make_dummy_canonical(
            "wf_2", "Legal.yxmd",
            business_purpose="Tracks litigation matters, contracts, and legal arbitration proceedings.",
            target_files=["Litigation.xlsx"], output_columns=["Matter_ID", "Litigation_Status"]
        )
        wf_uw = _make_dummy_canonical(
            "wf_3", "Underwriting.yxmd",
            business_purpose="Evaluates policy underwriting eligibility, coverage limits, and premium calculations.",
            target_files=["Policy_Underwriting.xlsx"], output_columns=["Policy_ID", "Premium"]
        )
        wf_sales = _make_dummy_canonical(
            "wf_4", "Sales.yxmd",
            business_purpose="Monitors product sales revenue, customer order pipelines, and distributor channels.",
            target_files=["Sales_Revenue.xlsx"], output_columns=["Sales_Amount", "Commission"]
        )
        wf_actuarial = _make_dummy_canonical(
            "wf_5", "Actuarial.yxmd",
            business_purpose="Performs actuarial valuation, loss development triangulation, and IBNR reserve estimation.",
            target_files=["Actuarial_IBNR.xlsx"], output_columns=["Accident_Year", "IBNR_Reserve"]
        )

        portfolio = build_portfolio_analysis([
            ("Claims.yxmd", "Claims.yxmd", wf_claims),
            ("Legal.yxmd", "Legal.yxmd", wf_legal),
            ("Underwriting.yxmd", "Underwriting.yxmd", wf_uw),
            ("Sales.yxmd", "Sales.yxmd", wf_sales),
            ("Actuarial.yxmd", "Actuarial.yxmd", wf_actuarial),
        ])

        # Exactly 5 configured business areas
        assert len(portfolio.business_areas) == 5
        domain_names = [g.business_area for g in portfolio.business_areas]
        assert domain_names == ["Claims & Risk", "Legal", "Underwriting", "Sales & Distribution", "Actuarial"]

        for group in portfolio.business_areas:
            assert group.workflow_count == 1
            assert len(group.workflows) == 1

        # Check operational data presence on workflow summaries
        for wf_summary in portfolio.workflows:
            assert hasattr(wf_summary, "last_run")
            assert hasattr(wf_summary, "frequency")
            summary_dict = wf_summary.to_dict()
            assert "last_run" in summary_dict
            assert "frequency" in summary_dict
            # Verify DTO serialization
            dto = PortfolioWorkflowSummaryDTO(**summary_dict)
            assert dto.last_run is not None
            assert dto.frequency is not None

    def test_business_area_scoped_metrics_distribution(self):
        """Criticality and Complexity distributions are properly scoped per business area."""
        wf_claims_1 = _make_dummy_canonical(
            "wf_1", "Claims_High.yxmd",
            business_purpose="Processes insurance claim losses and claimant exposure.",
            target_files=["Claims_Loss.xlsx", "Claims_Audit.xlsx", "Claims_Ledger.xlsx", "Claims_BI.xlsx", "Claims_Extract.xlsx"],
            output_columns=["Claim_ID", "Loss_Amount"]
        )
        wf_claims_2 = _make_dummy_canonical(
            "wf_2", "Claims_Low.yxmd",
            business_purpose="Generates simple claims volume reference listing.",
            target_files=["Claims_List.xlsx"],
            output_columns=["Claim_ID"]
        )
        wf_actuarial = _make_dummy_canonical(
            "wf_3", "Actuarial_Valuation.yxmd",
            business_purpose="Performs actuarial valuation, loss development triangulation, and IBNR reserve estimation.",
            target_files=["Actuarial_IBNR.xlsx"],
            output_columns=["Accident_Year", "IBNR_Reserve"]
        )

        portfolio = build_portfolio_analysis([
            ("Claims_High.yxmd", "Claims_High.yxmd", wf_claims_1),
            ("Claims_Low.yxmd", "Claims_Low.yxmd", wf_claims_2),
            ("Actuarial_Valuation.yxmd", "Actuarial_Valuation.yxmd", wf_actuarial),
        ])

        claims_group = next(g for g in portfolio.business_areas if g.business_area == "Claims & Risk")
        assert claims_group.workflow_count == 2
        assert len(claims_group.workflows) == 2

        actuarial_group = next(g for g in portfolio.business_areas if g.business_area == "Actuarial")
        assert actuarial_group.workflow_count == 1
        assert len(actuarial_group.workflows) == 1

        legal_group = next(g for g in portfolio.business_areas if g.business_area == "Legal")
        assert legal_group.workflow_count == 0
        assert len(legal_group.workflows) == 0

        # Scope verification: Claims workflows do not leak into Actuarial or Legal
        claims_crit_levels = [w.criticality_level for w in claims_group.workflows]
        actuarial_crit_levels = [w.criticality_level for w in actuarial_group.workflows]
        legal_crit_levels = [w.criticality_level for w in legal_group.workflows]

        assert len(claims_crit_levels) == 2
        assert len(actuarial_crit_levels) == 1
        assert len(legal_crit_levels) == 0
