"""Tests for business-facing DOCX report structure and content."""

from pathlib import Path
import docx
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow


class TestDocxBusinessReport:
    """Validate executive report formatting, absence of support tags, and summary inclusion."""

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
        assert "1. Executive Summary" in full_text
        assert "2. Workflow at a Glance" in full_text
        assert "3. Workflow Steps" in full_text
        assert "4. Data Flow & Lineage Paths" in full_text

        # 3. Tool business summaries present
        assert "Reads records from supported files" in full_text
        assert "Splits incoming data streams" in full_text
        assert "Writes workflow data to files" in full_text

    def test_join_workflow_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "join_report"
        analyze_workflow("fixtures/joins/join_workflow.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in join_workflow DOCX!"

        assert "Combines two data streams" in full_text
        assert "Aggregates and summarizes data" in full_text

    def test_mixed_complex_docx_business_report(self, tmp_path: Path):
        out_dir = tmp_path / "complex_report"
        analyze_workflow("fixtures/registry_mixed_complex.yxmd", out_dir)
        docx_file = out_dir / "workflow.docx"
        assert docx_file.exists()

        full_text = self._extract_all_docx_text(docx_file)

        for term in self.FORBIDDEN_USER_FACING_TERMS:
            assert term not in full_text, f"Forbidden term '{term}' found in complex DOCX!"
