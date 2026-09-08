"""
Test suite for Deterministic Directional Data-Superset Merge Detection in ETL Rationalisation.
"""

import pytest
from pathlib import Path

from awa.model.portfolio import (
    PortfolioWorkflowSummary,
    PortfolioAnalysis,
    WorkflowFingerprint,
    ColumnEvidence,
    DataSubsumptionEvidence,
)
from awa.parser.xml_parser import parse_workflow
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.analysis.rationalisation_analyzer import (
    build_workflow_fingerprint,
    compare_workflows,
    evaluate_directional_data_subsumption,
    evaluate_consolidation_rules,
    detect_candidate_from_comparison,
    build_rationalisation_analysis,
    ConsolidationRules,
)


@pytest.fixture
def bbcfood_results():
    """Parse and analyze BBCFood v2 and BBCFoodAggr workflows from test fixtures / uploads."""
    data_dir = Path("/Users/surya/Documents/Projects/Alteryx")
    file_v2 = None
    file_aggr = None

    for p in data_dir.glob("**/*.yxmd"):
        if p.name == "BBCFood v2.yxmd":
            file_v2 = p
        elif p.name == "BBCFoodAggr.yxmd":
            file_aggr = p

    if not file_v2 or not file_aggr:
        pytest.skip("BBCFood test workflows not found in workspace.")

    res_v2 = analyze_canonical(file_v2)
    res_aggr = analyze_canonical(file_aggr)

    summary_v2 = PortfolioWorkflowSummary(
        workflow_id="wf_bbcfood_v2",
        filename="BBCFood v2.yxmd",
        relative_path="BBCFood v2.yxmd",
        status="SUCCESS",
        node_count=len(res_v2.workflow.tools),
        connection_count=len(res_v2.workflow.connections),
        sources=list(res_v2.sources.keys()) if hasattr(res_v2, "sources") else [],
        targets=list(res_v2.targets.keys()) if hasattr(res_v2, "targets") else [],
        inspection_sinks=[],
        tool_types=list({t.tool_type for t in res_v2.workflow.tools.values()}),
        business_purpose="BBC Food Recipe Scraper and Consolidated Store",
        sttm_mappings_count=0,
        complexity_level="MEDIUM",
        complexity_score=45.0,
        criticality_level="LOW",
        criticality_score=20.0,
        frequency="Daily",
    )

    summary_aggr = PortfolioWorkflowSummary(
        workflow_id="wf_bbcfood_aggr",
        filename="BBCFoodAggr.yxmd",
        relative_path="BBCFoodAggr.yxmd",
        status="SUCCESS",
        node_count=len(res_aggr.workflow.tools),
        connection_count=len(res_aggr.workflow.connections),
        sources=list(res_aggr.sources.keys()) if hasattr(res_aggr, "sources") else [],
        targets=[],
        inspection_sinks=["Browse (Tool #5)"],
        tool_types=list({t.tool_type for t in res_aggr.workflow.tools.values()}),
        business_purpose="BBC Food Aggregate View",
        sttm_mappings_count=0,
        complexity_level="LOW",
        complexity_score=15.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
    )

    return {
        "v2": (summary_v2, res_v2),
        "aggr": (summary_aggr, res_aggr),
    }


def test_directional_subsumption_bbcfood(bbcfood_results):
    """Verify that BBCFoodAggr has 100% data coverage in BBCFood v2, but fails consolidation hard gate (37% <= 60% source overlap)."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_aggr, fp_v2)

    # 1. Forward direction: BBCFoodAggr -> BBCFood v2 (100% data coverage, but source overlap 37% <= 60%)
    subsumed_fwd, ev_fwd = evaluate_directional_data_subsumption(fp_aggr, fp_v2, comp)
    assert subsumed_fwd is False, "BBCFoodAggr should NOT qualify for merge because source overlap <= 60%"
    assert ev_fwd is not None
    assert ev_fwd.data_coverage_pct == 1.0
    assert ev_fwd.missing_fields_count == 0
    assert ev_fwd.processing_compatibility == "SUPPORTED"
    assert len(ev_fwd.shared_required_fields) > 0


def test_asymmetric_rejection_reverse_direction(bbcfood_results):
    """Verify that BBCFood v2 is NOT subsumed by BBCFoodAggr (strictly directional)."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_v2, fp_aggr)

    # 2. Reverse direction: BBCFood v2 -> BBCFoodAggr
    subsumed_rev, ev_rev = evaluate_directional_data_subsumption(fp_v2, fp_aggr, comp)
    assert subsumed_rev is False, "BBCFood v2 must NOT be subsumed by BBCFoodAggr"


def test_consolidation_rule_and_candidate_detection(bbcfood_results):
    """Verify that consolidation rule returns DO NOT MERGE when source overlap <= 60% and candidate becomes SHARED_LOGIC."""
    summary_v2, res_v2 = bbcfood_results["v2"]
    summary_aggr, res_aggr = bbcfood_results["aggr"]

    fp_v2 = build_workflow_fingerprint(summary_v2, res_v2)
    fp_aggr = build_workflow_fingerprint(summary_aggr, res_aggr)

    comp = compare_workflows(fp_aggr, fp_v2)
    decision = evaluate_consolidation_rules(fp_aggr, fp_v2, comp)

    assert decision.recommendation == "DO NOT MERGE"

    cand = detect_candidate_from_comparison(comp, fp_aggr, fp_v2)
    assert cand is not None
    assert cand.recommendation_type in ("RETIRE", "REVIEW", "SHARED_LOGIC")


def test_synthetic_missing_field_rejection():
    """Verify that a synthetic workflow with missing fields is rejected."""
    fp_source = WorkflowFingerprint(
        workflow_id="src_1",
        workflow_name="source_wf",
        sources=["input.csv"],
        source_types={"input.csv": "FILE"},
        source_fields={"input.csv": ["id", "amount", "missing_col"]},
        production_targets=[],
        inspection_sinks=["Browse"],
        output_schemas={},
        output_grain=["UNKNOWN"],
        tool_types=["DbFileInput", "BrowseV2"],
        transformation_signatures=[],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=[],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=2,
        edge_count=1,
        dag_depth=1,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "BrowseV2"],
        complexity_level="LOW",
        complexity_score=10.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "id": ColumnEvidence(original_name="id", normalized_name="id", source_dataset="input.csv", provenance="Input", is_required=True),
            "amount": ColumnEvidence(original_name="amount", normalized_name="amount", source_dataset="input.csv", provenance="Input", is_required=True),
            "missing_col": ColumnEvidence(original_name="missing_col", normalized_name="missing_col", source_dataset="input.csv", provenance="Input", is_required=True),
        },
        required_columns=["id", "amount", "missing_col"],
        available_columns=["id", "amount", "missing_col"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[],
    )

    fp_target = WorkflowFingerprint(
        workflow_id="tgt_1",
        workflow_name="target_wf",
        sources=["input.csv"],
        source_types={"input.csv": "FILE"},
        source_fields={"input.csv": ["id", "amount"]},
        production_targets=["output.yxdb"],
        inspection_sinks=[],
        output_schemas={"output.yxdb": ["id", "amount"]},
        output_grain=["UNKNOWN"],
        tool_types=["DbFileInput", "DbFileOutput"],
        transformation_signatures=[],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=[],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=2,
        edge_count=1,
        dag_depth=1,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "DbFileOutput"],
        complexity_level="LOW",
        complexity_score=10.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "id": ColumnEvidence(original_name="id", normalized_name="id", source_dataset="input.csv", provenance="Input", is_required=True),
            "amount": ColumnEvidence(original_name="amount", normalized_name="amount", source_dataset="input.csv", provenance="Input", is_required=True),
        },
        required_columns=["id", "amount"],
        available_columns=["id", "amount"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[],
    )

    comp = compare_workflows(fp_source, fp_target)
    subsumed, ev = evaluate_directional_data_subsumption(fp_source, fp_target, comp)

    assert subsumed is False
    assert ev.missing_fields_count == 1
    assert "missing_col" in ev.missing_fields


def test_embedded_csv_headers_and_subsumption_workflow_01_and_wf02():
    """Verify that Workflow A with embedded CSV headers in TextInput and Join is subsumed by Workflow B."""
    fp_a = WorkflowFingerprint(
        workflow_id="wf_01",
        workflow_name="Workflow_01.yxmd",
        sources=["textinput_8_field1", "textinput_11_field1", "textinput_19_field1"],
        source_types={"textinput_8_field1": "FILE", "textinput_11_field1": "FILE", "textinput_19_field1": "FILE"},
        source_fields={"textinput_8_field1": ["field1"]},
        production_targets=[],
        inspection_sinks=["Browse (Tool #15)"],
        output_schemas={},
        output_grain=["UNKNOWN"],
        tool_types=["TextInput", "TextToColumns", "Join", "Unique", "BrowseV2"],
        transformation_signatures=["Join on: Claim_ID=Claim_ID", "Unique deduplication on Claim_ID"],
        filters=[],
        join_keys=["Claim_ID=Claim_ID"],
        aggregations=[],
        formulas=["DateTimeDiff([Claim_Date], [Loss_Date], 'days')"],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=12,
        edge_count=11,
        dag_depth=5,
        branch_points=1,
        merge_points=1,
        topological_sequence=["TextInput", "TextToColumns", "Join", "Unique", "BrowseV2"],
        complexity_level="LOW",
        complexity_score=18.0,
        criticality_level="LOW",
        criticality_score=15.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="Claim_ID", normalized_name="claim_id", source_dataset="TextInput (Tool #8)", provenance="TextInput #8 embedded CSV header", sample_values=["CLM0001", "CLM0002"], is_required=True),
            "diagnosis_type": ColumnEvidence(original_name="Diagnosis_Type", normalized_name="diagnosis_type", source_dataset="TextInput (Tool #8)", provenance="TextInput #8 embedded CSV header", sample_values=["Disability", "Accident"], is_required=True),
            "icd_code": ColumnEvidence(original_name="ICD_Code", normalized_name="icd_code", source_dataset="TextInput (Tool #8)", provenance="TextInput #8 embedded CSV header", sample_values=["M54.5", "S93.4"], is_required=True),
        },
        required_columns=["claim_id", "diagnosis_type", "icd_code"],
        available_columns=["claim_id", "diagnosis_type", "icd_code", "field1"],
        raw_data_rows_inspected=26,
        sample_data_evidence=[
            {"field": "Claim_ID", "normalized": "claim_id", "tool_id": "8", "tool_type": "TextInput", "samples": ["CLM0001", "CLM0002"], "row_count": 26},
            {"field": "Diagnosis_Type", "normalized": "diagnosis_type", "tool_id": "8", "tool_type": "TextInput", "samples": ["Disability", "Accident"], "row_count": 26},
            {"field": "ICD_Code", "normalized": "icd_code", "tool_id": "8", "tool_type": "TextInput", "samples": ["M54.5", "S93.4"], "row_count": 26},
        ],
        operations_summary=[
            {"tool_id": "9", "tool_type": "Join", "operation": "Join on Claim_ID=Claim_ID", "keys": ["Claim_ID=Claim_ID"]},
            {"tool_id": "10", "tool_type": "Unique", "operation": "Unique deduplication on Claim_ID", "fields": ["Claim_ID"]},
        ],
    )

    fp_b = WorkflowFingerprint(
        workflow_id="wf_02",
        workflow_name="WF02.yxmd",
        sources=["source_13", "source_19", "source_26", "textinput_14_field1", "textinput_1_claim_id_ltd_transition_flag", "textinput_8_field1"],
        source_types={"source_13": "FILE", "source_19": "FILE", "source_26": "FILE", "textinput_14_field1": "FILE", "textinput_1_claim_id_ltd_transition_flag": "FILE", "textinput_8_field1": "FILE"},
        source_fields={"source_13": ["claim_id", "diagnosis_type", "icd_code", "gender", "state", "region", "zipcode", "salary_band"]},
        production_targets=["Consolidated_Claims.yxdb"],
        inspection_sinks=[],
        output_schemas={"Consolidated_Claims.yxdb": ["claim_id", "diagnosis_type", "icd_code", "gender", "state", "region", "zipcode", "salary_band"]},
        output_grain=["Claim_ID"],
        tool_types=["TextInput", "Join", "Unique", "Filter", "Formula", "Union", "DbFileOutput"],
        transformation_signatures=["Join on: Claim_ID=Claim_ID", "Unique deduplication on Claim_ID", "Formula: DateTimeDiff"],
        filters=["[Diagnosis_Type] != 'Unknown'"],
        join_keys=["Claim_ID=Claim_ID"],
        aggregations=[],
        formulas=["DateTimeDiff([Claim_Date], [Loss_Date], 'days')"],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=35,
        edge_count=38,
        dag_depth=8,
        branch_points=3,
        merge_points=2,
        topological_sequence=["TextInput", "Join", "Unique", "Filter", "Formula", "Union", "DbFileOutput"],
        complexity_level="MEDIUM",
        complexity_score=45.0,
        criticality_level="LOW",
        criticality_score=20.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="Claim_ID", normalized_name="claim_id", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=True),
            "diagnosis_type": ColumnEvidence(original_name="Diagnosis_Type", normalized_name="diagnosis_type", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=True),
            "icd_code": ColumnEvidence(original_name="ICD_Code", normalized_name="icd_code", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=True),
            "gender": ColumnEvidence(original_name="Gender", normalized_name="gender", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=False),
            "state": ColumnEvidence(original_name="State", normalized_name="state", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=False),
            "zipcode": ColumnEvidence(original_name="ZIPCode", normalized_name="zipcode", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=False),
            "salary_band": ColumnEvidence(original_name="Salary_Band", normalized_name="salary_band", source_dataset="Consolidated_Claims.yxdb", provenance="Input", is_required=False),
        },
        required_columns=["claim_id", "diagnosis_type", "icd_code", "gender", "state", "zipcode", "salary_band"],
        available_columns=["claim_id", "diagnosis_type", "icd_code", "gender", "state", "region", "zipcode", "salary_band"],
        raw_data_rows_inspected=150,
        sample_data_evidence=[
            {"field": "Claim_ID", "normalized": "claim_id", "tool_id": "1", "tool_type": "TextInput", "samples": ["CLM0001", "CLM0002", "CLM0003"], "row_count": 150},
        ],
        operations_summary=[
            {"tool_id": "15", "tool_type": "Join", "operation": "Join on Claim_ID=Claim_ID", "keys": ["Claim_ID=Claim_ID"]},
            {"tool_id": "16", "tool_type": "Unique", "operation": "Unique deduplication on Claim_ID", "fields": ["Claim_ID"]},
            {"tool_id": "17", "tool_type": "Filter", "operation": "Filter predicate: [Diagnosis_Type] != 'Unknown'", "expression": "[Diagnosis_Type] != 'Unknown'"},
            {"tool_id": "18", "tool_type": "Union", "operation": "Union of input datasets (Mode: ByName)", "mode": "ByName"},
        ],
    )

    comp = compare_workflows(fp_a, fp_b)

    # 1. Source Metadata Overlap recognises the 3 shared fields (3 / 9 = 33.3%)
    assert comp.metrics.source_overlap == pytest.approx(3 / 9, 0.001), "Source Metadata Overlap must recognize shared fields"
    assert comp.shared_source_fields == ["claim_id", "diagnosis_type", "icd_code"]
    assert comp.shared_sources == ["textinput_8_field1"]

    # 2. Forward Direction A -> B: 100% Data Field Coverage, but source overlap (33.3% <= 60%) fails merge hard gate
    subsumed_fwd, ev_fwd = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed_fwd is False, "Workflow_01 cannot be merged into WF02 because source overlap is <= 60%"
    assert ev_fwd is not None
    assert ev_fwd.data_coverage_pct == 1.0
    assert ev_fwd.missing_fields_count == 0
    assert ev_fwd.processing_compatibility == "SUPPORTED"
    assert ev_fwd.output_compatibility in ("INSPECTION_SINK_ONLY", "COMPATIBLE")
    assert ev_fwd.has_unresolved_unique_functionality is False
    assert set(ev_fwd.shared_required_fields) == {"claim_id", "diagnosis_type", "icd_code"}

    # 3. Reverse Direction B -> A: Must be rejected
    subsumed_rev, ev_rev = evaluate_directional_data_subsumption(fp_b, fp_a, comp)
    assert subsumed_rev is False, "WF02 cannot be subsumed into Workflow_01"
    assert ev_rev is not None
    assert ev_rev.missing_fields_count > 0

    # 4. Consolidation rule returns DO NOT MERGE and candidate is SHARED_LOGIC
    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "DO NOT MERGE"

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand is not None
    assert cand.recommendation_type == "SHARED_LOGIC"


def test_shared_formulae_preserved_when_missing_required_data():
    """Verify that SHARED_LOGIC (Shared Formulae) is preserved when merge gates fail due to missing fields."""
    fp_a = WorkflowFingerprint(
        workflow_id="wf_alpha",
        workflow_name="Alpha.yxmd",
        sources=["alpha_src.csv"],
        source_types={"alpha_src.csv": "FILE"},
        source_fields={"alpha_src.csv": ["claim_id", "unique_alpha_code"]},
        production_targets=["Alpha_Out.xlsx"],
        inspection_sinks=[],
        output_schemas={"Alpha_Out.xlsx": ["claim_id", "unique_alpha_code", "calc_diff"]},
        output_grain=["claim_id"],
        tool_types=["DbFileInput", "Formula", "DbFileOutput"],
        transformation_signatures=["Formula: calc_diff = DateTimeDiff([Date_A], [Date_B], 'days')"],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=["DateTimeDiff([Date_A], [Date_B], 'days')"],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=3,
        edge_count=2,
        dag_depth=3,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "Formula", "DbFileOutput"],
        complexity_level="MEDIUM",
        complexity_score=40.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="alpha_src.csv", is_required=True),
            "unique_alpha_code": ColumnEvidence(original_name="unique_alpha_code", normalized_name="unique_alpha_code", source_dataset="alpha_src.csv", is_required=True),
        },
        required_columns=["claim_id", "unique_alpha_code"],
        available_columns=["claim_id", "unique_alpha_code", "calc_diff"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[
            {"tool_id": "2", "tool_type": "Formula", "operation": "Formula: calc_diff = DateTimeDiff", "target_field": "calc_diff"},
        ],
    )

    fp_b = WorkflowFingerprint(
        workflow_id="wf_beta",
        workflow_name="Beta.yxmd",
        sources=["beta_src.csv"],
        source_types={"beta_src.csv": "FILE"},
        source_fields={"beta_src.csv": ["claim_id", "beta_col"]},
        production_targets=["Beta_Out.xlsx"],
        inspection_sinks=[],
        output_schemas={"Beta_Out.xlsx": ["claim_id", "beta_col", "calc_diff"]},
        output_grain=["claim_id"],
        tool_types=["DbFileInput", "Formula", "DbFileOutput"],
        transformation_signatures=["Formula: calc_diff = DateTimeDiff([Date_A], [Date_B], 'days')"],
        filters=[],
        join_keys=[],
        aggregations=[],
        formulas=["DateTimeDiff([Date_A], [Date_B], 'days')"],
        has_python=False,
        has_r=False,
        has_macros=False,
        node_count=3,
        edge_count=2,
        dag_depth=3,
        branch_points=0,
        merge_points=0,
        topological_sequence=["DbFileInput", "Formula", "DbFileOutput"],
        complexity_level="MEDIUM",
        complexity_score=40.0,
        criticality_level="LOW",
        criticality_score=10.0,
        frequency="Daily",
        downstream_consumers=[],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="beta_src.csv", is_required=True),
            "beta_col": ColumnEvidence(original_name="beta_col", normalized_name="beta_col", source_dataset="beta_src.csv", is_required=True),
        },
        required_columns=["claim_id", "beta_col"],
        available_columns=["claim_id", "beta_col", "calc_diff"],
        raw_data_rows_inspected=0,
        sample_data_evidence=[],
        operations_summary=[
            {"tool_id": "2", "tool_type": "Formula", "operation": "Formula: calc_diff = DateTimeDiff", "target_field": "calc_diff"},
        ],
    )

    comp = compare_workflows(fp_a, fp_b)

    # Directional subsumption must FAIL (Beta does not have unique_alpha_code)
    subsumed_fwd, ev_fwd = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed_fwd is False
    assert "unique_alpha_code" in ev_fwd.missing_fields

    # Decision must NOT be MERGE
    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "DO NOT MERGE"

    # Candidate recommendation must remain SHARED_LOGIC (Shared Formulae)
    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand is not None
    assert cand.recommendation_type == "SHARED_LOGIC"


def test_xml_textinput_csv_header_extraction():
    """Verify that extract_workflow_column_and_data_evidence parses embedded CSV headers from <Data><r><c>."""
    from awa.model.tool import Tool, ToolConfiguration
    from awa.model.workflow import Workflow, WorkflowMetadata
    from awa.model.field import Field
    from awa.model.analysis_result import CanonicalAnalysisResult
    from awa.analysis.rationalisation_analyzer import extract_workflow_column_and_data_evidence

    xml_textinput = """
    <Configuration>
        <NumRows value="5" />
        <Fields>
            <Field name="Field1" />
        </Fields>
        <Data>
            <r>
                <c>Claim_ID,Diagnosis_Type,ICD_Code</c>
            </r>
            <r>
                <c>CLM0001,Disability,M54.5</c>
            </r>
            <r>
                <c>CLM0002,Accident,S93.4</c>
            </r>
            <r>
                <c>CLM0003,Disability,M54.5</c>
            </r>
        </Data>
    </Configuration>
    """

    xml_join = """
    <Configuration>
        <JoinInfo connection="Left">
            <Field field="Claim_ID" />
        </JoinInfo>
        <JoinInfo connection="Right">
            <Field field="Claim_ID" />
        </JoinInfo>
        <SelectConfiguration>
            <Configuration outputConnection="Join">
                <SelectFields>
                    <SelectField field="Left_Claim_ID" selected="True" />
                    <SelectField field="Right_Diagnosis_Type" selected="True" rename="Diagnosis_Type" />
                    <SelectField field="Right_ICD_Code" selected="True" rename="ICD_Code" />
                </SelectFields>
            </Configuration>
        </SelectConfiguration>
    </Configuration>
    """

    xml_unique = """
    <Configuration>
        <UniqueFields>
            <Field field="Claim_ID" />
        </UniqueFields>
    </Configuration>
    """

    tool_input = Tool(
        tool_id=8,
        plugin="AlteryxBasePluginsGui.TextInput.TextInput",
        tool_type="TextInput",
        name="Claims Data Input",
        position=None,
        configuration=ToolConfiguration(raw_xml=xml_textinput, parsed={"fields": ["Field1"]}),
        output_fields=[
            Field(name="Claim_ID", type="V_WString"),
            Field(name="Diagnosis_Type", type="V_WString"),
            Field(name="ICD_Code", type="V_WString"),
        ],
    )

    tool_join = Tool(
        tool_id=9,
        plugin="AlteryxBasePluginsGui.Join.Join",
        tool_type="Join",
        name="Join on Claim_ID",
        position=None,
        configuration=ToolConfiguration(raw_xml=xml_join, parsed={}),
    )

    tool_unique = Tool(
        tool_id=10,
        plugin="AlteryxBasePluginsGui.Unique.Unique",
        tool_type="Unique",
        name="Deduplicate Claims",
        position=None,
        configuration=ToolConfiguration(raw_xml=xml_unique, parsed={}),
    )

    wf = Workflow(
        tools={8: tool_input, 9: tool_join, 10: tool_unique},
        connections=[],
        metadata=WorkflowMetadata(name="Workflow_01.yxmd", version="2021.4"),
    )

    from unittest.mock import MagicMock
    res = MagicMock(workflow=wf, lineage=None)

    summary = PortfolioWorkflowSummary(
        workflow_id="wf_01",
        filename="Workflow_01.yxmd",
        relative_path="Workflow_01.yxmd",
        status="SUCCESS",
        node_count=3,
        connection_count=2,
    )

    cols, req_cols, avail_cols, rows_cnt, sample_ev, ops = extract_workflow_column_and_data_evidence(summary, res)

    # 1. Available columns must contain the extracted CSV business headers
    assert "claim_id" in avail_cols
    assert "diagnosis_type" in avail_cols
    assert "icd_code" in avail_cols

    # 2. Required columns must identify the join key & deduplication key
    assert "claim_id" in req_cols

    # 3. Sample values must be captured from the subsequent data rows
    assert rows_cnt >= 4
    claim_sample = next((s for s in sample_ev if s["normalized"] == "claim_id"), None)
    assert claim_sample is not None
    assert "CLM0001" in claim_sample["samples"]
    assert "CLM0002" in claim_sample["samples"]

    diag_sample = next((s for s in sample_ev if s["normalized"] == "diagnosis_type"), None)
    assert diag_sample is not None
    assert "Disability" in diag_sample["samples"]


def test_merge_candidate_admissible_bounds_and_llm_immutability():
    """Verify that a candidate with MERGE recommendation has admissible=['CONSOLIDATE'] and cannot be downgraded by LLM."""
    import json
    from unittest.mock import MagicMock
    from awa.analysis.rationalisation_analyzer import enrich_candidate_with_llm, detect_candidate_from_comparison, compare_workflows
    from awa.model.portfolio import ConsolidationDecision

    # Build fingerprints where WF_A is subsumed by WF_B
    fp_a = WorkflowFingerprint(
        workflow_id="wf_01",
        workflow_name="Workflow_01.yxmd",
        sources=["source_a.csv"],
        production_targets=[],
        inspection_sinks=["Browse (Tool #5)"],
        source_fields={"source_a.csv": ["claim_id", "diagnosis_type", "icd_code", "claim_amount"]},
        transformation_signatures=["join:claim_id", "filter:claim_id"],
        complexity_level="LOW",
        criticality_level="LOW",
        frequency="Daily",
        available_columns=["claim_id", "diagnosis_type", "icd_code", "claim_amount"],
        required_columns=["claim_id", "diagnosis_type", "icd_code"],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_03",
        workflow_name="WF03.yxmd",
        sources=["source_b.csv"],
        production_targets=["claims_mart.yxdb"],
        inspection_sinks=[],
        source_fields={"source_b.csv": ["claim_id", "diagnosis_type", "icd_code", "claim_amount", "member_id"]},
        output_schemas={"claims_mart.yxdb": ["claim_id", "diagnosis_type", "icd_code", "claim_amount", "member_id"]},
        transformation_signatures=["join:claim_id", "filter:claim_id", "formula:calculate_risk"],
        complexity_level="MEDIUM",
        criticality_level="HIGH",
        frequency="Daily",
        available_columns=["claim_id", "diagnosis_type", "icd_code", "claim_amount", "member_id"],
        required_columns=["claim_id", "diagnosis_type"],
    )

    comp = compare_workflows(fp_a, fp_b)
    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)

    assert cand is not None
    assert cand.recommendation_type == "CONSOLIDATE"
    assert cand.admissible_recommendations == ["CONSOLIDATE"]
    assert cand.consolidation_decision is not None
    assert cand.consolidation_decision.recommendation == "MERGE"

    # Even if LLM returns SHARED_LOGIC, candidate recommendation_type MUST stay CONSOLIDATE
    mock_client = MagicMock()
    mock_client.generate.return_value = json.dumps({
        "recommendation": "SHARED_LOGIC",
        "workflow_ids": ["wf_01", "wf_03"],
        "reasoning": "Both workflows process claims.",
    })
    mock_generator = MagicMock(client=mock_client)

    enriched = enrich_candidate_with_llm(cand, mock_generator, {"wf_01", "wf_03"}, {"source_a.csv", "source_b.csv"})
    assert enriched.recommendation_type == "CONSOLIDATE"


# ===========================================================================
# REGRESSION TEST SUITE: Source Metadata Overlap via Field-Level Metadata
# ===========================================================================

def test_source_metadata_overlap_test1_same_file_same_fields():
    """TEST 1 — SAME FILE, SAME FIELDS: Exact source identity matches & source metadata overlap = 100%."""
    fp_a = WorkflowFingerprint(
        workflow_id="wf_a",
        workflow_name="Workflow_A.yxmd",
        sources=["source.csv"],
        available_columns=["claim_id", "diagnosis_type", "icd_code"],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="source.csv"),
            "diagnosis_type": ColumnEvidence(original_name="diagnosis_type", normalized_name="diagnosis_type", source_dataset="source.csv"),
            "icd_code": ColumnEvidence(original_name="icd_code", normalized_name="icd_code", source_dataset="source.csv"),
        },
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_b",
        workflow_name="Workflow_B.yxmd",
        sources=["source.csv"],
        available_columns=["claim_id", "diagnosis_type", "icd_code"],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="source.csv"),
            "diagnosis_type": ColumnEvidence(original_name="diagnosis_type", normalized_name="diagnosis_type", source_dataset="source.csv"),
            "icd_code": ColumnEvidence(original_name="icd_code", normalized_name="icd_code", source_dataset="source.csv"),
        },
    )

    comp = compare_workflows(fp_a, fp_b)

    assert comp.shared_sources == ["source"]
    assert comp.shared_source_fields == ["claim_id", "diagnosis_type", "icd_code"]
    assert comp.metrics.source_overlap == 1.0


def test_source_metadata_overlap_test2_different_files_same_fields():
    """TEST 2 — DIFFERENT FILE IDENTIFIERS, SAME FIELDS:
    Source object names differ (TextInput #8 != TextInput #13), but field metadata overlap = 100%.
    """
    fp_a = WorkflowFingerprint(
        workflow_id="wf_a",
        workflow_name="Workflow_A.yxmd",
        sources=["textinput_8_field1"],
        available_columns=["claim_id", "diagnosis_type", "icd_code"],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="TextInput (Tool #8)"),
            "diagnosis_type": ColumnEvidence(original_name="diagnosis_type", normalized_name="diagnosis_type", source_dataset="TextInput (Tool #8)"),
            "icd_code": ColumnEvidence(original_name="icd_code", normalized_name="icd_code", source_dataset="TextInput (Tool #8)"),
        },
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_b",
        workflow_name="Workflow_B.yxmd",
        sources=["textinput_13_field1"],
        available_columns=["claim_id", "diagnosis_type", "icd_code"],
        canonical_columns={
            "claim_id": ColumnEvidence(original_name="claim_id", normalized_name="claim_id", source_dataset="TextInput (Tool #13)"),
            "diagnosis_type": ColumnEvidence(original_name="diagnosis_type", normalized_name="diagnosis_type", source_dataset="TextInput (Tool #13)"),
            "icd_code": ColumnEvidence(original_name="icd_code", normalized_name="icd_code", source_dataset="TextInput (Tool #13)"),
        },
    )

    comp = compare_workflows(fp_a, fp_b)

    # Exact source identity differs
    assert comp.shared_sources == []
    # But field metadata overlap is 100%!
    assert comp.shared_source_fields == ["claim_id", "diagnosis_type", "icd_code"]
    assert comp.metrics.source_overlap == 1.0


def test_source_metadata_overlap_test3_different_files_partial_fields():
    """TEST 3 — DIFFERENT SOURCE OBJECTS, PARTIAL FIELD OVERLAP:
    Workflow A = {A, B, C, D}, Workflow B = {A, B, C, E, F} -> 3 shared / 6 union = 50% overlap.
    """
    fp_a = WorkflowFingerprint(
        workflow_id="wf_a",
        workflow_name="Workflow_A.yxmd",
        sources=["source_a.csv"],
        available_columns=["a", "b", "c", "d"],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_b",
        workflow_name="Workflow_B.yxmd",
        sources=["source_b.csv"],
        available_columns=["a", "b", "c", "e", "f"],
    )

    comp = compare_workflows(fp_a, fp_b)

    assert comp.shared_sources == []
    assert comp.shared_source_fields == ["a", "b", "c"]
    assert comp.metrics.source_overlap == 0.50  # 3 / 6


def test_source_metadata_overlap_test4_no_field_overlap():
    """TEST 4 — NO FIELD OVERLAP:
    Workflow A = {A, B}, Workflow B = {X, Y} -> 0 shared / 4 union = 0% overlap.
    """
    fp_a = WorkflowFingerprint(
        workflow_id="wf_a",
        workflow_name="Workflow_A.yxmd",
        sources=["source_a.csv"],
        available_columns=["a", "b"],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_b",
        workflow_name="Workflow_B.yxmd",
        sources=["source_b.csv"],
        available_columns=["x", "y"],
    )

    comp = compare_workflows(fp_a, fp_b)

    assert comp.shared_sources == []
    assert comp.shared_source_fields == []
    assert comp.metrics.source_overlap == 0.0


def test_source_metadata_overlap_test5_data_superset_symmetry_and_directional_coverage():
    """TEST 5 — DATA-SUPERSET CASE:
    Workflow A = {A, B, C}
    Workflow B = {A, B, C, D, E}
    Source Metadata Overlap: 3 / 5 = 60% (Symmetric: Overlap(A, B) == Overlap(B, A)).
    Data Coverage A -> B: 100%.
    Data Coverage B -> A: 60%.
    """
    fp_a = WorkflowFingerprint(
        workflow_id="wf_a",
        workflow_name="Workflow_A.yxmd",
        sources=["feed_a.csv"],
        available_columns=["a", "b", "c"],
        required_columns=["a", "b", "c"],
        inspection_sinks=["Browse (Tool #5)"],
        production_targets=[],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_b",
        workflow_name="Workflow_B.yxmd",
        sources=["feed_b.csv"],
        available_columns=["a", "b", "c", "d", "e"],
        required_columns=["a", "b", "c", "d", "e"],
        production_targets=["output_mart.yxdb"],
        inspection_sinks=[],
    )

    comp_ab = compare_workflows(fp_a, fp_b)
    comp_ba = compare_workflows(fp_b, fp_a)

    # 1. Source Metadata Overlap is strictly symmetric (3 / 5 = 60%)
    assert comp_ab.metrics.source_overlap == 0.60
    assert comp_ba.metrics.source_overlap == 0.60
    assert comp_ab.metrics.source_overlap == comp_ba.metrics.source_overlap
    assert comp_ab.shared_source_fields == ["a", "b", "c"]
    assert comp_ba.shared_source_fields == ["a", "b", "c"]

    # 2. Data Subsumption Coverage is strictly directional
    # In this case, 3 / 5 = 60.0% exactly, which fails the strict >60% hard gate
    subsumed_fwd, ev_fwd = evaluate_directional_data_subsumption(fp_a, fp_b, comp_ab)
    assert subsumed_fwd is False
    assert ev_fwd.data_coverage_pct == 1.0
    assert ev_fwd.missing_fields_count == 0

    subsumed_rev, ev_rev = evaluate_directional_data_subsumption(fp_b, fp_a, comp_ba)
    assert subsumed_rev is False
    assert ev_rev.data_coverage_pct == 0.60
    assert ev_rev.missing_fields_count == 2
    assert set(ev_rev.missing_fields) == {"d", "e"}

    # When overlap strictly exceeds 60% (e.g. 4/5 = 80%), subsumed is True
    fp_a_4 = WorkflowFingerprint(
        workflow_id="wf_a4",
        workflow_name="Workflow_A4.yxmd",
        sources=["feed_a.csv"],
        available_columns=["a", "b", "c", "d"],
        required_columns=["a", "b", "c", "d"],
        inspection_sinks=["Browse (Tool #5)"],
        production_targets=[],
    )
    comp_a4_b = compare_workflows(fp_a_4, fp_b)
    assert comp_a4_b.metrics.source_overlap == 0.80
    subsumed_a4, ev_a4 = evaluate_directional_data_subsumption(fp_a_4, fp_b, comp_a4_b)
    assert subsumed_a4 is True
    assert ev_a4.data_coverage_pct == 1.0


def test_source_metadata_overlap_test6_workflow_01_and_wf03_real_world_regression():
    """TEST 6 — REAL-WORLD REGRESSION: Workflow_01.yxmd and WF03.yxmd
    Recognises 7 matching source fields, non-zero Source Metadata Overlap, 100% Data Coverage,
    and final recommendation = CONSOLIDATE / MERGE.
    """
    fields_01 = [
        "claim_id", "diagnosis_type", "icd_code", "month_end_date",
        "payment_amount", "payment_date", "payment_id"
    ]
    fields_03 = [
        "claim_id", "diagnosis_type", "icd_code", "month_end_date",
        "payment_amount", "payment_date", "payment_id",
        "member_id", "policy_number", "provider_id", "claim_status"
    ]

    fp_01 = WorkflowFingerprint(
        workflow_id="wf_01",
        workflow_name="Workflow_01.yxmd",
        sources=["textinput_8_field1", "textinput_1_claim_id"],
        source_types={"textinput_8_field1": "FILE", "textinput_1_claim_id": "FILE"},
        source_fields={"textinput_8_field1": fields_01},
        available_columns=fields_01,
        required_columns=fields_01,
        canonical_columns={f: ColumnEvidence(original_name=f, normalized_name=f, source_dataset="TextInput #8", is_required=True) for f in fields_01},
        production_targets=[],
        inspection_sinks=["Browse (Tool #5)"],
        tool_types=["TextInput", "Join", "Unique", "Browse"],
        transformation_signatures=["Join on: claim_id=claim_id", "Unique deduplication on claim_id"],
        complexity_level="LOW",
        criticality_level="LOW",
        frequency="Daily",
    )
    fp_03 = WorkflowFingerprint(
        workflow_id="wf_03",
        workflow_name="WF03.yxmd",
        sources=["claims_lake_source.csv", "payments_feed.yxdb"],
        source_types={"claims_lake_source.csv": "FILE", "payments_feed.yxdb": "FILE"},
        source_fields={"claims_lake_source.csv": fields_03},
        available_columns=fields_03,
        required_columns=["claim_id", "diagnosis_type", "payment_id"],
        canonical_columns={f: ColumnEvidence(original_name=f, normalized_name=f, source_dataset="claims_lake_source.csv", is_required=True) for f in fields_03},
        production_targets=["Consolidated_Payments_Mart.yxdb"],
        inspection_sinks=[],
        output_schemas={"Consolidated_Payments_Mart.yxdb": fields_03},
        tool_types=["InputData", "Join", "Unique", "Formula", "OutputData"],
        transformation_signatures=["Join on: claim_id=claim_id", "Unique deduplication on claim_id", "Formula: calculate_risk"],
        complexity_level="MEDIUM",
        criticality_level="HIGH",
        frequency="Daily",
    )

    comp = compare_workflows(fp_01, fp_03)

    # 1. 7 shared source fields recognised
    assert comp.shared_source_fields == sorted(fields_01)
    assert len(comp.shared_source_fields) == 7

    # 2. Source Metadata Overlap is non-zero (7 / 11 = ~63.6%)
    expected_overlap = len(set(fields_01) & set(fields_03)) / len(set(fields_01) | set(fields_03))
    assert comp.metrics.source_overlap == pytest.approx(expected_overlap, 0.001)
    assert comp.metrics.source_overlap > 0.60

    # 3. Data Coverage A -> B is 100%
    subsumed, ev = evaluate_directional_data_subsumption(fp_01, fp_03, comp)
    assert subsumed is True
    assert ev.data_coverage_pct == 1.0
    assert ev.missing_fields_count == 0
    assert len(ev.shared_required_fields) == 7

    # 4. Final recommendation is CONSOLIDATE / MERGE
    decision = evaluate_consolidation_rules(fp_01, fp_03, comp)
    assert decision.recommendation == "MERGE"
    assert decision.matched_rule == ConsolidationRules.RULE_DATA_SUBSUMPTION

    cand = detect_candidate_from_comparison(comp, fp_01, fp_03)
    assert cand is not None
    assert cand.recommendation_type == "CONSOLIDATE"
    assert cand.admissible_recommendations == ["CONSOLIDATE"]


# =========================================================================
# SECTION 9 VERIFICATION EXAMPLES & BOUNDARY TESTS
# =========================================================================

def test_hard_gate_example_1_high_overlap_full_coverage_supported():
    """Example 1: Source Overlap 72%, Data Coverage 100%, Processing SUPPORTED -> MERGE / CONSOLIDATE."""
    cols_a = [f"col_{i}" for i in range(1, 9)]  # 8 cols
    cols_b = [f"col_{i}" for i in range(1, 12)]  # 11 cols (8/11 = ~72.7%)
    fp_a = WorkflowFingerprint(
        workflow_id="wf_ex1_a",
        workflow_name="Workflow_EX1_A.yxmd",
        sources=["feed_a.csv"],
        available_columns=cols_a,
        required_columns=cols_a,
        inspection_sinks=["Browse (Tool #1)"],
        production_targets=[],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_ex1_b",
        workflow_name="Workflow_EX1_B.yxmd",
        sources=["feed_b.csv"],
        available_columns=cols_b,
        required_columns=cols_b,
        production_targets=["target.yxdb"],
        inspection_sinks=[],
    )
    comp = compare_workflows(fp_a, fp_b)
    assert comp.metrics.source_overlap > 0.60
    subsumed, ev = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed is True
    assert ev.data_coverage_pct == 1.0

    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "MERGE"

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand.recommendation_type == "CONSOLIDATE"


def test_hard_gate_example_2_low_overlap_full_coverage_rejected():
    """Example 2: Source Overlap 3%, Data Coverage 100% -> DO NOT MERGE (Hard gate rejects)."""
    # Create 1 shared col out of 33 cols -> 1/33 = 3.03%
    shared = ["shared_1"]
    cols_a = shared  # required: shared_1
    cols_b = shared + [f"extra_{i}" for i in range(1, 33)]  # 33 total
    fp_a = WorkflowFingerprint(
        workflow_id="wf_ex2_a",
        workflow_name="Workflow_EX2_A.yxmd",
        sources=["feed_a.csv"],
        available_columns=cols_a,
        required_columns=cols_a,
        inspection_sinks=["Browse (Tool #1)"],
        production_targets=[],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_ex2_b",
        workflow_name="Workflow_EX2_B.yxmd",
        sources=["feed_b.csv"],
        available_columns=cols_b,
        required_columns=cols_b,
        production_targets=["target.yxdb"],
        inspection_sinks=[],
    )
    comp = compare_workflows(fp_a, fp_b)
    assert comp.metrics.source_overlap <= 0.60
    assert pytest.approx(comp.metrics.source_overlap, abs=0.01) == 0.03

    subsumed, ev = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed is False  # Fails hard gate
    assert ev.data_coverage_pct == 1.0  # Even though column coverage is 100%

    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "DO NOT MERGE"
    assert "60%" in decision.reason

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand is None or cand.recommendation_type != "CONSOLIDATE"


def test_hard_gate_example_3_high_overlap_missing_required_fields():
    """Example 3: Source Overlap 85%, Missing 2 Required Fields -> DO NOT MERGE (Data Sufficiency fails)."""
    cols_common = [f"c_{i}" for i in range(1, 18)]  # 17 common
    cols_a_only = ["req_missing_1", "req_missing_2"]  # 2 missing in B
    cols_a = cols_common + cols_a_only  # 19 cols
    cols_b = cols_common + ["other_b"]  # 18 cols
    # Union = 17 common + 2 A + 1 B = 20 cols. Intersection = 17 / 20 = 85.0%
    fp_a = WorkflowFingerprint(
        workflow_id="wf_ex3_a",
        workflow_name="Workflow_EX3_A.yxmd",
        sources=["feed_a.csv"],
        available_columns=cols_a,
        required_columns=cols_a,  # all required including missing
        inspection_sinks=["Browse (Tool #1)"],
        production_targets=[],
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_ex3_b",
        workflow_name="Workflow_EX3_B.yxmd",
        sources=["feed_b.csv"],
        available_columns=cols_b,
        required_columns=cols_b,
        production_targets=["target.yxdb"],
        inspection_sinks=[],
    )
    comp = compare_workflows(fp_a, fp_b)
    assert comp.metrics.source_overlap == 0.85

    subsumed, ev = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed is False
    assert ev.missing_fields_count == 2
    assert set(ev.missing_fields) == {"req_missing_1", "req_missing_2"}

    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "DO NOT MERGE"

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand is None or cand.recommendation_type != "CONSOLIDATE"


def test_hard_gate_example_4_high_overlap_full_coverage_incompatible_processing():
    """Example 4: Source Overlap 90%, Data Coverage 100%, Processing Incompatible -> DO NOT MERGE."""
    cols_common = [f"c_{i}" for i in range(1, 10)]  # 9 common
    cols_a = cols_common  # 9 cols
    cols_b = cols_common + ["b_extra"]  # 10 cols. 9 / 10 = 90.0%
    fp_a = WorkflowFingerprint(
        workflow_id="wf_ex4_a",
        workflow_name="Workflow_EX4_A.yxmd",
        sources=["feed_a.csv"],
        available_columns=cols_a,
        required_columns=cols_a,
        inspection_sinks=[],
        production_targets=["prod_a.yxdb"],
        output_schemas={"prod_a.yxdb": cols_a},
        tool_types=["InputData", "Summarize", "OutputData"],
        operations_summary=[{"tool_id": "2", "tool_type": "Summarize", "operation": "GroupBy(c_1), Sum(c_2)"}],
        transformation_signatures=["Summarize: GroupBy(c_1), Sum(c_2)"],
        complexity_level="HIGH",
        criticality_level="HIGH",
    )
    fp_b = WorkflowFingerprint(
        workflow_id="wf_ex4_b",
        workflow_name="Workflow_EX4_B.yxmd",
        sources=["feed_b.csv"],
        available_columns=cols_b,
        required_columns=cols_b,
        production_targets=["prod_b.yxdb"],
        output_schemas={"prod_b.yxdb": ["different_1", "different_2"]},
        tool_types=["InputData", "Join", "OutputData"],
        operations_summary=[{"tool_id": "3", "tool_type": "Join", "operation": "Join on: x=y"}],
        transformation_signatures=["Join on: x=y"],
        complexity_level="LOW",
        criticality_level="LOW",
    )
    comp = compare_workflows(fp_a, fp_b)
    assert comp.metrics.source_overlap == 0.90

    # fp_a has Summarize which fp_b lacks -> processing_compatibility is UNSUPPORTED
    subsumed, ev = evaluate_directional_data_subsumption(fp_a, fp_b, comp)
    assert subsumed is False
    assert ev.processing_compatibility == "UNSUPPORTED"

    decision = evaluate_consolidation_rules(fp_a, fp_b, comp)
    assert decision.recommendation == "DO NOT MERGE"

    cand = detect_candidate_from_comparison(comp, fp_a, fp_b)
    assert cand is None or cand.recommendation_type != "CONSOLIDATE"


def test_hard_gate_boundary_strict_inequality():
    """Boundary test: 60.0% -> DO NOT MERGE (Fails strict >60%). 60.1% -> MERGE."""
    # 60.0% exactly: 3 / 5 = 0.6000000000
    fp_a_60 = WorkflowFingerprint(
        workflow_id="wf_60",
        workflow_name="Workflow_60.yxmd",
        sources=["feed_60.csv"],
        available_columns=["a", "b", "c"],
        required_columns=["a", "b", "c"],
        inspection_sinks=["Browse"],
        production_targets=[],
    )
    fp_b_60 = WorkflowFingerprint(
        workflow_id="wf_b60",
        workflow_name="Workflow_B60.yxmd",
        sources=["feed_b60.csv"],
        available_columns=["a", "b", "c", "d", "e"],
        required_columns=["a", "b", "c", "d", "e"],
        production_targets=["target.yxdb"],
        inspection_sinks=[],
    )
    comp_60 = compare_workflows(fp_a_60, fp_b_60)
    assert comp_60.metrics.source_overlap == 0.60
    subsumed_60, ev_60 = evaluate_directional_data_subsumption(fp_a_60, fp_b_60, comp_60)
    assert subsumed_60 is False
    decision_60 = evaluate_consolidation_rules(fp_a_60, fp_b_60, comp_60)
    assert decision_60.recommendation == "DO NOT MERGE"

    # >60% (e.g. 60.1% or 601 / 1000):
    common_601 = [f"f_{i}" for i in range(601)]
    extra_b = [f"extra_{i}" for i in range(399)]
    fp_a_601 = WorkflowFingerprint(
        workflow_id="wf_601",
        workflow_name="Workflow_601.yxmd",
        sources=["feed_601.csv"],
        available_columns=common_601,
        required_columns=common_601,
        inspection_sinks=["Browse"],
        production_targets=[],
    )
    fp_b_1000 = WorkflowFingerprint(
        workflow_id="wf_1000",
        workflow_name="Workflow_1000.yxmd",
        sources=["feed_1000.csv"],
        available_columns=common_601 + extra_b,
        required_columns=common_601 + extra_b,
        production_targets=["target.yxdb"],
        inspection_sinks=[],
    )
    comp_601 = compare_workflows(fp_a_601, fp_b_1000)
    assert comp_601.metrics.source_overlap == 0.601
    assert comp_601.metrics.source_overlap > 0.60
    subsumed_601, ev_601 = evaluate_directional_data_subsumption(fp_a_601, fp_b_1000, comp_601)
    assert subsumed_601 is True
    decision_601 = evaluate_consolidation_rules(fp_a_601, fp_b_1000, comp_601)
    assert decision_601.recommendation == "MERGE"





