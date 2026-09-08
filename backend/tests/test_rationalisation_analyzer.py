import pytest
from awa.analysis.rationalisation_analyzer import (
    WorkflowFingerprint,
    build_workflow_fingerprint,
    compare_workflows,
    detect_candidate_from_comparison,
    build_rationalisation_analysis,
)
from awa.model.analysis_result import CanonicalAnalysisResult
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, ToolConfiguration, Position
from awa.model.field import Field
from awa.model.source_info import SourceInfo
from awa.model.portfolio import (
    PortfolioWorkflowSummary,
    PortfolioAnalysis,
    PortfolioAggregateMetrics,
    RationalisationAnalysis,
    RationalisationCandidate,
)


def _make_dummy_workflow(wid: str, name: str, sources: list[str], targets: list[str], fields: list[str]) -> tuple[PortfolioWorkflowSummary, CanonicalAnalysisResult]:
    summary = PortfolioWorkflowSummary(
        workflow_id=wid,
        filename=f"{name}.yxmd",
        relative_path=f"{name}.yxmd",
        complexity_level="MEDIUM",
        criticality_level="HIGH",
        complexity_score=50.0,
        criticality_score=50.0,
        sources=sources,
        targets=targets,
        status="SUCCESS",
    )
    tools = {
        1: Tool(
            tool_id=1,
            plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
            tool_type="DbFileInput",
            name="Input",
            position=Position(x=10, y=10),
            configuration=ToolConfiguration(raw_xml="", parsed={"clean_sources": sources, "clean_fields": fields}),
            output_fields=[Field(name=f, type="V_WString") for f in fields],
        ),
        2: Tool(
            tool_id=2,
            plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
            tool_type="DbFileOutput",
            name="Output",
            position=Position(x=100, y=10),
            configuration=ToolConfiguration(raw_xml="", parsed={"clean_targets": targets, "clean_fields": fields}),
            output_fields=[Field(name=f, type="V_WString") for f in fields],
        ),
    }
    wf = Workflow(
        metadata=WorkflowMetadata(name=name, version="2023.1"),
        tools=tools,
        connections=[],
    )
    res = CanonicalAnalysisResult(
        analysis_id=f"res_{wid}",
        source=SourceInfo(source_format="yxmd", original_filename=f"{name}.yxmd"),
        workflow=wf,
        graph=None,
        execution_order=[1, 2],
        translations={},
        consumed_anchors={},
        lineage_paths=[],
        metrics=None,
        dag_layout=None,
        python_trace=None,
        tool_explanations={},
        required_libraries=[],
        diagnostics=[],
    )
    return summary, res


def test_fingerprint_target_schema_extraction():
    summary, wf_res = _make_dummy_workflow(
        wid="wf-1",
        name="Orders Workflow",
        sources=["Orders.csv"],
        targets=["Analytics.Orders_Final"],
        fields=["order_id", "customer_id", "total_amt"],
    )
    fp = build_workflow_fingerprint(summary, wf_res)
    assert any("orders" in s.lower() for s in fp.sources)
    assert any("orders_final" in t for t in fp.production_targets)
    assert any("order_id" in cols for cols in fp.output_schemas.values())


def test_pairwise_directional_subsumption_and_schema_overlap():
    s_target, wf_target = _make_dummy_workflow(
        wid="wf-101",
        name="Target Workflow (Superset)",
        sources=["Customer_Master.csv", "Transactions.csv", "Region_Ref.csv"],
        targets=["Target_Analytics.DW_Cust_Trans"],
        fields=["cust_id", "trans_id", "amt", "region_code"],
    )
    s_absorbed, wf_absorbed = _make_dummy_workflow(
        wid="wf-102",
        name="Absorbed Workflow (Subset)",
        sources=["Customer_Master.csv", "Transactions.csv"],
        targets=["Absorbed_Reporting.Tbl_Summary"],
        fields=["cust_id", "trans_id", "amt"],
    )

    fp_target = build_workflow_fingerprint(s_target, wf_target)
    fp_absorbed = build_workflow_fingerprint(s_absorbed, wf_absorbed)

    comp = compare_workflows(fp_target, fp_absorbed)
    cand = detect_candidate_from_comparison(comp, fp_target, fp_absorbed)
    assert cand is not None
    assert cand.recommendation_type in ("CONSOLIDATE", "MERGE")
    # Directional subsumption: source_overlap should be 1.0
    assert cand.deterministic_metrics.source_overlap == 1.0
    # Schema field overlap should be calculated even if target physical paths differ
    assert cand.deterministic_metrics.target_overlap >= 0.50
    # Rationale should be business-facing without raw metric dumps
    assert "0." not in cand.reasoning


def test_rationalisation_unique_workflow_partitioning():
    s_a, wf_a = _make_dummy_workflow(
        wid="wf-1",
        name="Workflow A",
        sources=["Source1.csv", "Source2.csv"],
        targets=["Target1.csv"],
        fields=["f1", "f2", "f3"],
    )
    s_b, wf_b = _make_dummy_workflow(
        wid="wf-2",
        name="Workflow B",
        sources=["Source1.csv"],
        targets=["Target1.csv"],
        fields=["f1", "f2"],
    )
    s_c, wf_c = _make_dummy_workflow(
        wid="wf-3",
        name="Workflow C Unique",
        sources=["UniqueSource.csv"],
        targets=["UniqueTarget.csv"],
        fields=["u1", "u2"],
    )

    portfolio = PortfolioAnalysis(
        portfolio_id="test_p",
        portfolio_name="Test Portfolio",
        workflow_count=3,
        workflows=[s_a, s_b, s_c],
        metrics=PortfolioAggregateMetrics(
            total_workflows=3,
            successful_workflows=3,
            total_tools=6,
        ),
        shared_sources=[],
        shared_targets=[],
        relationships=[],
        rationalisation_candidates=[],
    )

    results = {
        "wf-1": wf_a,
        "wf-2": wf_b,
        "wf-3": wf_c,
    }

    analysis = build_rationalisation_analysis(
        portfolio=portfolio,
        successful_results=results,
        use_llm=False,
    )

    classifications = analysis.workflow_classifications
    assert len(classifications) == 3
    # Check that A and B are marked CONSOLIDATE, C is marked KEEP
    assert classifications["wf-1"] == "CONSOLIDATE"
    assert classifications["wf-2"] == "CONSOLIDATE"
    assert classifications["wf-3"] == "KEEP"

    # Verify summary counts match classifications
    consolidate_count = sum(1 for c in classifications.values() if c == "CONSOLIDATE")
    keep_count = sum(1 for c in classifications.values() if c == "KEEP")
    retire_count = sum(1 for c in classifications.values() if c == "RETIRE")

    assert analysis.workflow_counts["CONSOLIDATE"] == consolidate_count
    assert analysis.workflow_counts["KEEP"] == keep_count
    assert analysis.workflow_counts["RETIRE"] == retire_count
    assert analysis.analysed_workflow_count == consolidate_count + keep_count + retire_count


def test_frequency_overlap_alone_does_not_retire():
    # Two workflows with identical frequency (Daily) but completely different logic and targets
    s_a, wf_a = _make_dummy_workflow(
        wid="wf-1",
        name="Sales Ingest",
        sources=["Sales.csv"],
        targets=["Analytics.Daily_Sales"],
        fields=["sale_id", "amount"],
    )
    s_b, wf_b = _make_dummy_workflow(
        wid="wf-2",
        name="Inventory Audit",
        sources=["Inventory.csv"],
        targets=["Reports.Inventory_Audit"],
        fields=["item_id", "qty"],
    )
    s_a.frequency = "Daily"
    s_b.frequency = "Daily"

    fp_a = build_workflow_fingerprint(s_a, wf_a)
    fp_b = build_workflow_fingerprint(s_b, wf_b)

    comp = compare_workflows(fp_a, fp_b)
    assert comp.metrics.frequency_overlap == 1.0  # Same frequency

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    # Because targets are distinct and source overlap is 0, this must NOT be RETIRE
    if cand is not None:
        assert cand.recommendation_type != "RETIRE"
        assert cand.recommendation_type != "RETIRE_CANDIDATE"


def test_target_fields_and_provenance_population():
    s_a, wf_a = _make_dummy_workflow(
        wid="wf-1",
        name="Source Target Workflow",
        sources=["Sales.csv"],
        targets=["Analytics.Output_Tgt"],
        fields=["sale_id", "customer_name", "price"],
    )
    fp = build_workflow_fingerprint(s_a, wf_a)
    assert "output_tgt" in " ".join(fp.production_targets)
    assert "sale_id" in fp.available_columns
    assert any("sale_id" in flds for flds in fp.source_fields.values())


def test_distinct_evidence_models_required_vs_metadata_matching():
    # Retained workflow has 10 fields available
    s_target, wf_target = _make_dummy_workflow(
        wid="wf-101",
        name="Retained Master",
        sources=["Master.csv"],
        targets=["Analytics.DW_Final"],
        fields=["claim_id", "diagnosis_type", "icd_code", "month_end_date", "payment_amount", "payment_date", "payment_id", "extra_1", "extra_2", "extra_3"],
    )
    # Absorbed workflow requires 7 fields but also has extra common metadata
    s_absorbed, wf_absorbed = _make_dummy_workflow(
        wid="wf-102",
        name="Absorbed Process",
        sources=["Claims_Input.csv"],
        targets=["Analytics.Claims_Staging"],
        fields=["claim_id", "diagnosis_type", "icd_code", "month_end_date", "payment_amount", "payment_date", "payment_id", "extra_1", "extra_2"],
    )

    fp_target = build_workflow_fingerprint(s_target, wf_target)
    fp_absorbed = build_workflow_fingerprint(s_absorbed, wf_absorbed)

    comp = compare_workflows(fp_target, fp_absorbed)
    cand = detect_candidate_from_comparison(comp, fp_target, fp_absorbed)

    assert cand is not None
    # 1. Broader metadata matches (9 fields shared)
    assert len(cand.dependency_evidence.shared_source_fields) == 9
    # 2. Source fields by workflow populated for Claims_Input.csv
    src_fields = cand.source_fields_by_workflow.get(fp_absorbed.workflow_name, {})
    assert any("claim_id" in flds for flds in src_fields.values())


def test_target_metadata_overlap_acceptance_suite():
    # Acceptance Test 1: Distinct target files & 0 schema overlap -> target_overlap MUST be 0.0
    s_wf03, res_wf03 = _make_dummy_workflow(
        wid="wf-03",
        name="WF03",
        sources=["SourceA.csv"],
        targets=["Deliverable_43.csv", "Deliverable_45.csv", "Deliverable_46.csv"],
        fields=["f1", "f2"],
    )
    s_wf01, res_wf01 = _make_dummy_workflow(
        wid="wf-01",
        name="Workflow_01",
        sources=["SourceB.csv"],
        targets=["wf01_output_xlsx_sheet1.xlsx"],
        fields=["f3", "f4"],
    )
    # Clear output schemas to test schema-less target comparison
    fp_03 = build_workflow_fingerprint(s_wf03, res_wf03)
    fp_01 = build_workflow_fingerprint(s_wf01, res_wf01)
    fp_03.output_schemas.clear()
    fp_01.output_schemas.clear()

    comp1 = compare_workflows(fp_03, fp_01)
    assert comp1.metrics.target_overlap == 0.0
    assert comp1.metrics.schema_similarity == 0.0

    # Acceptance Test 2: Same target file, no schema available -> target_overlap > 0
    s_t2a, res_t2a = _make_dummy_workflow(
        wid="wf-t2a",
        name="WF_T2A",
        sources=["Src.csv"],
        targets=["claims_output.csv"],
        fields=["f1"],
    )
    s_t2b, res_t2b = _make_dummy_workflow(
        wid="wf-t2b",
        name="WF_T2B",
        sources=["Src.csv"],
        targets=["claims_output.csv"],
        fields=["f1"],
    )
    fp_t2a = build_workflow_fingerprint(s_t2a, res_t2a)
    fp_t2b = build_workflow_fingerprint(s_t2b, res_t2b)
    fp_t2a.output_schemas.clear()
    fp_t2b.output_schemas.clear()

    comp2 = compare_workflows(fp_t2a, fp_t2b)
    assert comp2.metrics.target_overlap == 1.0

    # Acceptance Test 3: Different target files, same output schema fields
    s_t3a, res_t3a = _make_dummy_workflow(
        wid="wf-t3a",
        name="WF_T3A",
        sources=["Src.csv"],
        targets=["claims_output.csv"],
        fields=["claim_id", "payment_date", "payment_amount"],
    )
    s_t3b, res_t3b = _make_dummy_workflow(
        wid="wf-t3b",
        name="WF_T3B",
        sources=["Src.csv"],
        targets=["claims_output.xlsx"],
        fields=["claim_id", "payment_date", "payment_amount"],
    )
    fp_t3a = build_workflow_fingerprint(s_t3a, res_t3a)
    fp_t3b = build_workflow_fingerprint(s_t3b, res_t3b)

    comp3 = compare_workflows(fp_t3a, fp_t3b)
    assert comp3.metrics.target_overlap == 1.0  # 100% schema match despite distinct filenames

    # Acceptance Test 5: Same logic & frequency & DAG, but completely different targets and schemas
    s_t5a, res_t5a = _make_dummy_workflow(
        wid="wf-t5a",
        name="WF_T5A",
        sources=["Src.csv"],
        targets=["target_alpha.csv"],
        fields=["alpha_id"],
    )
    s_t5b, res_t5b = _make_dummy_workflow(
        wid="wf-t5b",
        name="WF_T5B",
        sources=["Src.csv"],
        targets=["target_beta.csv"],
        fields=["beta_id"],
    )
    fp_t5a = build_workflow_fingerprint(s_t5a, res_t5a)
    fp_t5b = build_workflow_fingerprint(s_t5b, res_t5b)

    comp5 = compare_workflows(fp_t5a, fp_t5b)
    assert comp5.metrics.target_overlap == 0.0
    assert comp5.metrics.schema_similarity == 0.0



