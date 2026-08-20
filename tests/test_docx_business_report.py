"""Tests for business-facing DOCX report structure and content."""

from pathlib import Path
import docx
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow


class TestDocxBusinessReport:
    """Validate executive report formatting, absence of support tags, and structured business sections."""

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

    def test_simple_filter_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "simple_filter_report"
        analyze_workflow("fixtures/basic/simple_filter.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        # 1. No forbidden support classifications or diagnostic dumps
        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in simple_filter DOCX!"

        # 2. Executive report sections present
        assert "1. Executive Summary & Assessment" in full_text
        assert "2. Inputs & Target Business Deliverables" in full_text
        assert "3. What the Workflow Does (Business Process Stages)" in full_text
        assert "4. Key Business Rules" in full_text
        assert "5. Source-to-Target Data Lineage" in full_text
        assert "6. Initial Complexity & Governance Assessment" in full_text
        assert "7. Visual Workflow Graph (DAG)" in full_text
        assert "8. Step-by-Step Tool Specifications" in full_text
        assert "9. Technical Configuration Appendix" in full_text

        # 3. Governance fields
        assert "Workflow at a Glance" in full_text
        assert "Not documented" in full_text

        # 4. Tool business action and technical summary present
        assert "Business Action:" in full_text
        assert "Technical Function:" in full_text

    def test_join_workflow_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "join_report"
        analyze_workflow("fixtures/joins/join_workflow.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in join_workflow DOCX!"

        assert "1. Executive Summary & Assessment" in full_text
        assert "Business Action:" in full_text
        assert "Technical Function:" in full_text

    def test_demo_claims_volume_extract_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "claims_report"
        analyze_workflow("Demo_Claims_Volume_Extract_reconstructed.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        # Verify business sections & content
        assert "1. Executive Summary & Assessment" in full_text
        assert "Workflow at a Glance" in full_text
        assert "Business Purpose" in full_text
        assert "Why the Workflow Matters" in full_text
        assert "What Goes In" in full_text
        assert "What Comes Out" in full_text
        assert "Key Business Rules" in full_text
        assert "Source-to-Target Data Lineage" in full_text
        assert "Initial Complexity & Governance Assessment" in full_text
        assert "Step-by-Step Tool Specifications" in full_text
        assert "Technical Configuration Appendix" in full_text

        # Verify specific business facts
        assert "Claims Volume" in full_text
        assert "Policy Master" in full_text
        assert "Claim Payments" in full_text
        assert "Claim Diary Notes" in full_text
        assert "Historical Claims" in full_text
        assert "Product Type" in full_text
        assert "State" in full_text
        assert "Aging & Litigation Risk" in full_text

        # Verify governance facts explicitly distinguished
        assert "Not documented" in full_text
