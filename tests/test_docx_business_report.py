"""Tests for Executive Summary DOCX report structure, length, and content."""

from pathlib import Path
import docx
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow


class TestDocxBusinessReport:
    """Validate Executive Summary conforming to the professional Business Analyst assessment contract."""

    FORBIDDEN_USER_FACING_TERMS = [
        "Support Level",
        "FULL",
        "SUPPORTED",
        "PARTIAL",
        "PASS-THROUGH",
        "PASS_THROUGH",
        "DOCUMENTATION_ONLY",
        "EXTERNAL_EXECUTION",
        "UNSUPPORTED",
        "Analysis Diagnostics",
    ]

    def _extract_all_docx_text(self, docx_path: Path) -> str:
        doc = docx.Document(str(docx_path))
        text_parts = [p.text for p in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                text_parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(text_parts)

    def _extract_executive_summary_text(self, docx_path: Path) -> str:
        doc = docx.Document(str(docx_path))
        in_exec = False
        exec_lines = []
        for p in doc.paragraphs:
            if p.text == "1. Executive Summary":
                in_exec = True
            elif p.text.startswith("2. "):
                in_exec = False
            if in_exec:
                exec_lines.append(p.text)
        return "\n".join(exec_lines)

    def test_simple_filter_docx_business_report(self, tmp_path: Path):
        """Test on a simple single-branch filter workflow."""
        out_dir = tmp_path / "simple_filter_report"
        analyze_workflow("fixtures/basic/simple_filter.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)
        exec_text = self._extract_executive_summary_text(docx_file)

        # 1. No forbidden support classifications or diagnostic dumps
        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in simple_filter DOCX!"

        # 2. Executive Summary components present
        assert "1. Executive Summary" in exec_text
        assert "Methods of Analysis" in exec_text
        assert "Conclusions" in exec_text

        # 3. Concise length (100 to 350 words)
        words = len(exec_text.split())
        assert 50 <= words <= 350, f"Executive summary word count {words} out of expected range!"

        # 4. Report body sections present
        assert "5. Visual Workflow Graph (DAG Architecture)" in full_text
        assert "6. Step-by-Step Tool Specifications" in full_text
        assert "7. Technical Configuration Appendix" in full_text

        # 5. Tool business action and technical summary present in body
        assert "Business Action:" in full_text
        assert "Technical Function:" in full_text

    def test_join_workflow_docx_business_report(self, tmp_path: Path):
        """Test on a multi-input join workflow."""
        out_dir = tmp_path / "join_report"
        analyze_workflow("fixtures/joins/join_workflow.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)
        exec_text = self._extract_executive_summary_text(docx_file)

        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in join_workflow DOCX!"

        assert "1. Executive Summary" in exec_text
        assert "Methods of Analysis" in exec_text
        assert "Conclusions" in exec_text

        words = len(exec_text.split())
        assert 50 <= words <= 350

    def test_demo_claims_volume_extract_docx_business_report(self, tmp_path: Path):
        """Test on the full reconstructed Demo Claims regression fixture."""
        out_dir = tmp_path / "claims_report"
        analyze_workflow("Demo_Claims_Volume_Extract_reconstructed.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)
        exec_text = self._extract_executive_summary_text(docx_file)

        # Verify Executive Summary headings
        assert "1. Executive Summary" in exec_text
        assert "Methods of Analysis" in exec_text
        assert "Findings" in exec_text
        assert "Conclusions" in exec_text
        assert "Recommendations" in exec_text
        assert "Limitations" not in exec_text

        # Word count check (~100-350 words)
        words = len(exec_text.split())
        assert 100 <= words <= 350, f"Demo claims executive summary word count: {words}"

        # No raw tool IDs in Executive Summary
        assert "#1" not in exec_text
        assert "#39" not in exec_text

        # Verify body sections
        assert "2. Business Process & Operational Deliverables" in full_text
        assert "2.1 Inputs & Upstream Dependencies" in full_text
        assert "2.2 Outputs & Business Reporting Deliverables" in full_text
        assert "2.3 Sequential Operational Stages" in full_text
        assert "3. Key Business Rules & Transformations" in full_text
        assert "4. Source-to-Target Data Lineage" in full_text
        assert "5. Visual Workflow Graph (DAG Architecture)" in full_text
        assert "6. Step-by-Step Tool Specifications" in full_text
        assert "7. Technical Configuration Appendix" in full_text

        # Verify specific business facts in body
        assert "Claims Volume" in full_text
        assert "Policy Master" in full_text
        assert "Claim Payments" in full_text
        assert "Claim Diary Notes" in full_text
        assert "Historical Claims Extract" in full_text
        assert "Product Type Analysis" in full_text
        assert "State Analysis" in full_text
        assert "Aging & Litigation Risk Analysis" in full_text

    def test_conditional_rendering_omits_empty_sections(self, tmp_path: Path):
        """Verify that when metadata/rules/outputs are missing, their headings are completely omitted."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>raw_data.csv</File></Configuration></Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect"><Position x="150" y="50" /></GuiSettings>
      <Properties><Configuration /></Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output" />
      <Destination ToolID="2" Connection="Input" />
    </Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "no_output.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        out_dir = tmp_path / "no_output_report"
        analyze_workflow(wf_file, out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        # Because there are no business rules, Section 3 heading should NOT be rendered
        assert "3. Key Business Rules & Transformations" not in full_text

        # Because there are no outputs, Section 2.2 heading should NOT be rendered
        assert "2.2 Outputs & Business Reporting Deliverables" not in full_text

        # No empty headings or placeholder text
        assert "No information available" not in full_text
        assert "Business use not documented" not in full_text

    def test_download_docx_api_endpoint_contains_executive_summary(self):
        """Regression test: verify the FastAPI download endpoint returns populated Executive Summary in DOCX."""
        import io
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        analysis_id = resp.json()["analysis_id"]

        docx_resp = client.get(f"/api/download/{analysis_id}/docx")
        assert docx_resp.status_code == 200

        doc = docx.Document(io.BytesIO(docx_resp.content))
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert "1. Executive Summary" in headings
        assert "5. Visual Workflow Graph (DAG Architecture)" in headings

        # Verify text between "1. Executive Summary" and the next major heading is non-empty
        in_exec = False
        exec_lines = []
        for p in doc.paragraphs:
            if p.text == "1. Executive Summary":
                in_exec = True
            elif p.text.startswith("2. ") or p.text.startswith("5. "):
                in_exec = False
            if in_exec:
                exec_lines.append(p.text)

        exec_text = "\n".join(exec_lines)
        assert len(exec_text.split()) >= 100
        assert "Methods of Analysis" in exec_text
        assert "Findings" in exec_text
        assert "Conclusions" in exec_text
        assert "Recommendations" in exec_text
        assert "Limitations" not in exec_text
