"""Tests for deterministic Workflow Intelligence and Executive Business Assessment Engine."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from awa.parser.xml_parser import parse_workflow
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.analysis.business_intelligence import generate_business_summary
from awa.graph.builder import build_graph, execution_order
from backend.app.main import app
from backend.app.services.analyzer import to_overview_dto


class TestBusinessIntelligenceEngine:
    """Test suite validating structured facts, executive assessment, inputs/outputs, lineage, gaps, and disposition."""

    @pytest.fixture
    def demo_claims_workflow(self):
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        assert wf_path.exists(), "Demo_Claims fixture must exist"
        return parse_workflow(wf_path)

    def test_demo_claims_structured_business_facts(self, demo_claims_workflow):
        """Verify full structured business facts generation on the regression fixture."""
        graph = build_graph(demo_claims_workflow)
        exec_order = execution_order(graph)

        bs = generate_business_summary(demo_claims_workflow, graph, exec_order)

        # 1. Business Purpose (1-3 concise sentences, no technical jargon or tool numbers)
        assert bs.business_purpose != ""
        assert "claims" in bs.business_purpose.lower()
        assert bs.one_line_purpose != ""

        # 2. Source Inputs (4 inputs with concrete business roles & formats)
        assert len(bs.source_inputs) == 4
        input_names = [inp.name for inp in bs.source_inputs]
        assert any("Claims Volume" in name for name in input_names)
        assert any("Policy Master" in name for name in input_names)
        assert any("Claim Payments" in name for name in input_names)
        assert any("Claim Diary Notes" in name for name in input_names)

        for inp in bs.source_inputs:
            assert inp.source_type == "Excel Workbook"
            assert inp.business_role != ""
            assert inp.dependency_significance != ""
            assert len(inp.evidence) > 0

        # 3. Business Outputs (5 primary deliverables with business meaning & likely use)
        assert len(bs.business_outputs) == 5
        output_names = [out.name for out in bs.business_outputs]
        assert any("Historical" in name or "Claims" in name for name in output_names)
        assert any("Quarter" in name for name in output_names)
        assert any("Product" in name for name in output_names)
        assert any("State" in name for name in output_names)
        assert any("Aging" in name or "Risk" in name for name in output_names)

        for out in bs.business_outputs:
            assert out.destination_type == "Excel Workbook"
            assert out.business_meaning != ""
            assert out.likely_use != ""
            assert len(out.upstream_sources) > 0

        # 4. Processing Stages (8 container stages with short titles & progressive disclosure)
        assert len(bs.processing_stages) == 8
        for stg in bs.processing_stages:
            assert stg.short_title != ""
            assert stg.summary != ""
            assert stg.tool_count > 0

        # 5. Promoted Key Business Rules
        assert len(bs.business_rules) >= 5
        for r in bs.business_rules:
            assert r.description != ""
            assert r.evidence != ""

        # 6. Source-to-Target Lineage (Impact understanding)
        assert len(bs.lineage) == 5
        for lin in bs.lineage:
            assert lin.source_name != ""
            assert lin.transformation != ""
            assert lin.target_name != ""

        # 7. Executive Business Assessment
        assessment = bs.assessment
        assert assessment is not None
        assert assessment.platform == "Alteryx Designer"
        assert assessment.complexity in ("Low", "Moderate", "High")
        assert len(assessment.complexity_factors) > 0
        assert assessment.business_owner == "Not documented"
        assert assessment.schedule == "Not documented"
        assert assessment.criticality == "Not documented"
        assert assessment.assessment_status == "Automated assessment"

        # 8. Business Role & Value, Key Findings, Gaps, Disposition, Validation
        assert len(assessment.role_and_value) >= 2
        assert len(assessment.key_findings) >= 4
        assert len(assessment.assessment_gaps) >= 6
        assert assessment.preliminary_disposition == "Further assessment required"
        assert "stakeholder validation" in assessment.disposition_rationale.lower()
        assert len(assessment.validation_checklist) >= 6

        # 9. Structured Executive Summary (Business Analysis Standard)
        exec_sum = bs.executive_summary
        assert exec_sum is not None
        assert exec_sum.subject_and_purpose != ""
        assert exec_sum.methods_and_process != ""
        assert len(exec_sum.findings) >= 3
        assert exec_sum.conclusions != ""
        assert len(exec_sum.recommendations) >= 2
        assert len(exec_sum.limitations) == 0

        # Verify no tool IDs in executive summary
        assert "#" not in exec_sum.subject_and_purpose
        assert "#" not in exec_sum.methods_and_process
        for fnd in exec_sum.findings:
            assert "#" not in fnd
        assert "#" not in exec_sum.conclusions
        for r in exec_sum.recommendations:
            assert "#" not in r

    def test_determinism(self, demo_claims_workflow):
        """Verify that identical inputs produce 100% identical business facts."""
        graph = build_graph(demo_claims_workflow)
        exec_order = execution_order(graph)

        bs1 = generate_business_summary(demo_claims_workflow, graph, exec_order)
        bs2 = generate_business_summary(demo_claims_workflow, graph, exec_order)

        assert bs1.business_purpose == bs2.business_purpose
        assert bs1.one_line_purpose == bs2.one_line_purpose
        assert [i.to_dict() for i in bs1.source_inputs] == [i.to_dict() for i in bs2.source_inputs]
        assert [o.to_dict() for o in bs1.business_outputs] == [o.to_dict() for o in bs2.business_outputs]
        assert [r.to_dict() for r in bs1.business_rules] == [r.to_dict() for r in bs2.business_rules]
        assert bs1.assessment.to_dict() == bs2.assessment.to_dict()

    def test_synthetic_workflow_without_annotations_or_containers(self, tmp_path: Path):
        """Verify graceful degradation and proper 'Not documented' markers when metadata is missing."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>transactions.csv</File></Configuration></Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxSpatialPluginsGui.Summarize.Summarize"><Position x="150" y="50" /></GuiSettings>
      <Properties><Configuration></Configuration></Properties>
    </Node>
    <Node ToolID="3">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"><Position x="250" y="50" /></GuiSettings>
      <Properties><Configuration><File>revenue_summary.yxdb</File></Configuration></Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output" />
      <Destination ToolID="2" Connection="Input" />
    </Connection>
    <Connection>
      <Origin ToolID="2" Connection="Output" />
      <Destination ToolID="3" Connection="Input" />
    </Connection>
  </Connections>
</AlteryxDocument>
"""
        wf_file = tmp_path / "minimal.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        g = build_graph(wf)
        order = execution_order(g)

        bs = generate_business_summary(wf, g, order)

        assert bs.business_purpose != ""
        assert len(bs.source_inputs) == 1
        assert bs.source_inputs[0].name == "Transactions"
        assert bs.source_inputs[0].source_type == "CSV Data File"

        assert len(bs.business_outputs) == 1
        assert bs.business_outputs[0].name == "Revenue"
        assert bs.business_outputs[0].destination_type == "Alteryx Database File"

        assert len(bs.processing_stages) > 0
        assert bs.assessment.business_owner == "Not documented"
        assert bs.assessment.schedule == "Not documented"
        assert bs.assessment.criticality == "Not documented"
        assert bs.assessment.preliminary_disposition == "Further assessment required"

    def test_canonical_analysis_integration(self):
        """Verify CanonicalAnalysisResult and DTOs contain structured business facts."""
        canonical = analyze_canonical("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        assert canonical.business_summary is not None
        assert canonical.business_summary.business_purpose != ""

        overview_dto = to_overview_dto(canonical)
        assert overview_dto.business_summary is not None
        assert len(overview_dto.business_summary.source_inputs) == 4
        assert len(overview_dto.business_summary.business_outputs) == 5
        assert len(overview_dto.business_summary.business_rules) >= 5
        assert overview_dto.business_summary.assessment.business_owner == "Not documented"
        assert overview_dto.business_summary.assessment.preliminary_disposition == "Further assessment required"
        assert len(overview_dto.business_summary.assessment.key_findings) >= 4

    def test_api_upload_endpoint_returns_business_summary(self):
        """Verify the FastAPI /api/upload endpoint returns populated business_summary."""
        client = TestClient(app)

        with open("Demo_Claims_Volume_Extract_reconstructed.yxmd", "rb") as f:
            resp = client.post(
                "/api/upload",
                files={"file": ("Demo_Claims_Volume_Extract_reconstructed.yxmd", f, "application/octet-stream")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "business_summary" in data
        assert data["business_summary"] is not None
        bs = data["business_summary"]
        assert "claims" in bs["business_purpose"].lower()
        assert len(bs["source_inputs"]) == 4
        assert len(bs["business_outputs"]) == 5
        assert len(bs["processing_stages"]) == 8
        assert "business_rules" in bs
        assert len(bs["business_rules"]) >= 5
        assert bs["assessment"]["business_owner"] == "Not documented"
        assert bs["assessment"]["preliminary_disposition"] == "Further assessment required"
        assert len(bs["assessment"]["key_findings"]) >= 4
