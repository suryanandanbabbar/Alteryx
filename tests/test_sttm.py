"""Tests for Source-to-Target Mapping (STTM) extraction and Excel workbook generation."""

import io
from pathlib import Path
import openpyxl
import pytest
from fastapi.testclient import TestClient

from awa.analysis.workflow_analyzer import analyze_canonical, analyze_workflow
from awa.analysis.sttm_extractor import extract_sttm
from awa.generators.sttm_generator import generate_sttm_excel
from awa.parser.xml_parser import parse_workflow
from awa.graph.builder import build_graph, execution_order
from awa.analysis.business_intelligence import generate_business_summary
from backend.app.main import app


class TestSTTM:
    """Validate deterministic STTM extraction and Excel generation."""

    def test_demo_claims_sttm_extraction(self):
        """Verify field-level STTM mappings extracted for Demo Claims workflow."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        assert wf_path.exists()

        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        assert sttm.workflow_name != ""
        assert sttm.total_mappings >= 25, f"Expected at least 25 mappings, got {sttm.total_mappings}"

        target_tables = {m.target_table for m in sttm.mappings}
        assert any("Detail" in t or "Historical Claims" in t for t in target_tables)
        assert any("QuarterSummary" in t or "Volume Summary" in t for t in target_tables)
        assert any("Product Type" in t for t in target_tables)
        assert any("State" in t for t in target_tables)
        assert any("Aging" in t or "Risk" in t for t in target_tables)

        transformations = {m.transformation for m in sttm.mappings}
        assert "Direct" in transformations
        assert "Aggregation" in transformations
        assert "Pivot / Reshape" in transformations

        # Verify no tool IDs in user-facing table names
        for m in sttm.mappings:
            assert "#" not in m.source_table, f"Tool ID leaked into source table: {m.source_table}"
            assert "#" not in m.target_table, f"Tool ID leaked into target table: {m.target_table}"
            assert m.source_attribute != ""
            assert m.target_attribute != ""
            assert m.transformation_logic != ""

    def test_sttm_excel_generation(self, tmp_path: Path):
        """Verify generated Excel workbook formatting, sheets, and headers."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        canonical = analyze_canonical(wf_path)
        assert canonical.sttm is not None

        xlsx_path = tmp_path / "Demo_Claims_STTM.xlsx"
        generate_sttm_excel(canonical.sttm, xlsx_path)
        assert xlsx_path.exists()

        wb = openpyxl.load_workbook(xlsx_path)
        assert "Source-to-Target Mapping" in wb.sheetnames
        assert "STTM Summary" in wb.sheetnames

        ws1 = wb["Source-to-Target Mapping"]
        headers = [ws1.cell(1, col).value for col in range(1, 7)]
        expected_headers = [
            "Source Table",
            "Source Attribute",
            "Transformation",
            "Transformation Logic",
            "Target Table",
            "Target Attribute",
        ]
        assert headers == expected_headers

        # Verify data rows
        assert ws1.max_row > 10
        first_row_vals = [ws1.cell(2, col).value for col in range(1, 7)]
        assert all(v is not None and v != "" for v in first_row_vals)

        # Verify summary sheet
        ws2 = wb["STTM Summary"]
        assert ws2.cell(2, 2).value == "Source-to-Target Mapping Summary"
        assert ws2.max_row >= 10

    def test_direct_filter_sttm_synthetic(self, tmp_path: Path):
        """Test direct pass-through and filter mappings on a simple workflow."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>customers.csv</File></Configuration></Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Filter.Filter"><Position x="150" y="50" /></GuiSettings>
      <Properties><Configuration><Expression>[Age] &gt;= 21</Expression><Mode>Simple</Mode></Configuration></Properties>
    </Node>
    <Node ToolID="3">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"><Position x="250" y="50" /></GuiSettings>
      <Properties><Configuration><File>adult_customers.csv</File></Configuration></Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection>
      <Origin ToolID="1" Connection="Output" />
      <Destination ToolID="2" Connection="Input" />
    </Connection>
    <Connection>
      <Origin ToolID="2" Connection="True" />
      <Destination ToolID="3" Connection="Input" />
    </Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "filter_test.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        assert sttm.total_mappings >= 1
        mapping = sttm.mappings[0]
        assert "Customer" in mapping.source_table or "customers" in mapping.source_table.lower()
        assert "Adult" in mapping.target_table or "adult_customers" in mapping.target_table.lower()

    def test_rename_and_formula_sttm_synthetic(self, tmp_path: Path):
        """Test rename and formula calculations in STTM."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>sales.csv</File></Configuration></Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.AlteryxSelect.AlteryxSelect"><Position x="150" y="50" /></GuiSettings>
      <Properties><Configuration>
        <SelectFields>
          <SelectField field="price" selected="True" rename="unit_price" />
          <SelectField field="qty" selected="True" />
        </SelectFields>
      </Configuration></Properties>
    </Node>
    <Node ToolID="3">
      <GuiSettings Plugin="AlteryxBasePluginsGui.Formula.Formula"><Position x="250" y="50" /></GuiSettings>
      <Properties><Configuration>
        <FormulaFields>
          <FormulaField field="total_revenue" expression="[unit_price] * [qty]" type="Double" size="8" />
        </FormulaFields>
      </Configuration></Properties>
    </Node>
    <Node ToolID="4">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput"><Position x="350" y="50" /></GuiSettings>
      <Properties><Configuration><File>revenue_report.csv</File></Configuration></Properties>
    </Node>
  </Nodes>
  <Connections>
    <Connection><Origin ToolID="1" Connection="Output" /><Destination ToolID="2" Connection="Input" /></Connection>
    <Connection><Origin ToolID="2" Connection="Output" /><Destination ToolID="3" Connection="Input" /></Connection>
    <Connection><Origin ToolID="3" Connection="Output" /><Destination ToolID="4" Connection="Input" /></Connection>
  </Connections>
</AlteryxDocument>"""
        wf_file = tmp_path / "formula_test.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        wf = parse_workflow(wf_file)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        target_attrs = {m.target_attribute: m for m in sttm.mappings}
        assert "unit_price" in target_attrs
        assert target_attrs["unit_price"].transformation == "Rename"
        assert "total_revenue" in target_attrs
        assert target_attrs["total_revenue"].transformation == "Derived Calculation"

    def test_sttm_download_endpoint_and_bundle(self):
        """Verify the FastAPI STTM download endpoint and ZIP bundle inclusion."""
        client = TestClient(app)
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        analysis_id = resp.json()["analysis_id"]

        # 1. Test GET /api/download/{analysis_id}/sttm
        sttm_resp = client.get(f"/api/download/{analysis_id}/sttm")
        assert sttm_resp.status_code == 200
        assert "spreadsheetml" in sttm_resp.headers["Content-Type"]
        assert "STTM.xlsx" in sttm_resp.headers["Content-Disposition"]

        wb = openpyxl.load_workbook(io.BytesIO(sttm_resp.content))
        assert "Source-to-Target Mapping" in wb.sheetnames
        assert "STTM Summary" in wb.sheetnames

        # 2. Test GET /api/download/{analysis_id}/zip (bundle contains STTM)
        import zipfile
        zip_resp = client.get(f"/api/download/{analysis_id}/zip")
        assert zip_resp.status_code == 200
        assert "application/zip" in zip_resp.headers["Content-Type"]

        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            filenames = zf.namelist()
            assert any(f.endswith(".json") for f in filenames)
            assert any(f.endswith(".py") for f in filenames)
            assert any(f.endswith(".svg") for f in filenames)
            assert any(f.endswith(".docx") for f in filenames)
            assert any(f.endswith("_STTM.xlsx") or f.endswith("sttm.xlsx") for f in filenames)
