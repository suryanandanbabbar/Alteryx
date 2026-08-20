"""Tests for Executive Business Assessment DOCX report structure and content."""

from pathlib import Path
import docx
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow


class TestDocxBusinessReport:
    """Validate Executive Business Assessment formatting, absence of support tags, and structured business sections."""

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

        # 2. Executive Business Assessment and Technical sections present
        assert "1. Executive Business Assessment" in full_text
        assert "1.1 Workflow at a Glance" in full_text
        assert "1.2 Business Purpose" in full_text
        assert "1.3 Business Process" in full_text
        assert "1.4 Inputs & Dependencies" in full_text
        assert "1.5 Outputs & Business Use" in full_text
        assert "1.6 Business Lineage" in full_text
        assert "1.7 Business Role & Value" in full_text
        assert "1.8 Key Findings" in full_text
        assert "1.9 Assessment Gaps" in full_text
        assert "1.10 Preliminary Disposition" in full_text
        assert "1.11 Business Validation Required" in full_text

        assert "2. Visual Workflow Graph (DAG Architecture)" in full_text
        assert "3. Step-by-Step Tool Specifications" in full_text
        assert "4. Technical Configuration Appendix" in full_text

        # 3. Governance and validation fields
        assert "Alteryx Designer" in full_text
        assert "Not documented" in full_text
        assert "Further assessment required" in full_text
        assert "Pending Validation" in full_text

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

        assert "1. Executive Business Assessment" in full_text
        assert "1.1 Workflow at a Glance" in full_text
        assert "1.4 Inputs & Dependencies" in full_text
        assert "1.5 Outputs & Business Use" in full_text
        assert "1.10 Preliminary Disposition" in full_text
        assert "1.11 Business Validation Required" in full_text

    def test_demo_claims_volume_extract_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "claims_report"
        analyze_workflow("Demo_Claims_Volume_Extract_reconstructed.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        # Verify all 11 Executive Business Assessment subsections
        assert "1. Executive Business Assessment" in full_text
        assert "1.1 Workflow at a Glance" in full_text
        assert "1.2 Business Purpose" in full_text
        assert "1.3 Business Process" in full_text
        assert "1.4 Inputs & Dependencies" in full_text
        assert "1.5 Outputs & Business Use" in full_text
        assert "1.6 Business Lineage (Impact Mapping)" in full_text
        assert "1.7 Business Role & Value" in full_text
        assert "1.8 Key Findings" in full_text
        assert "1.9 Assessment Gaps (Unestablished Facts)" in full_text
        assert "1.10 Preliminary Disposition" in full_text
        assert "1.11 Business Validation Required" in full_text

        # Verify Technical sections
        assert "2. Visual Workflow Graph (DAG Architecture)" in full_text
        assert "3. Step-by-Step Tool Specifications" in full_text
        assert "4. Technical Configuration Appendix" in full_text

        # Verify specific business facts
        assert "Claims Volume" in full_text
        assert "Policy Master" in full_text
        assert "Claim Payments" in full_text
        assert "Claim Diary Notes" in full_text
        assert "Historical Claims Extract" in full_text
        assert "Product Type Analysis" in full_text
        assert "State Analysis" in full_text
        assert "Aging & Litigation Risk Analysis" in full_text

        # Verify governance facts explicitly distinguished
        assert "Not documented" in full_text
        assert "Further assessment required" in full_text
        assert "Pending Validation" in full_text
