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

    def test_claim_count_lineage(self):
        """Verify Claim Count in Product Type, State, and Aging summaries traces strictly to Claims Volume."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        # Find Claim Count mappings across outputs
        claim_count_mappings = [
            m for m in sttm.mappings if m.target_attribute in ("Claim Count", "Claim_Count")
        ]
        assert len(claim_count_mappings) == 3, f"Expected exactly 3 Claim Count mappings, got {len(claim_count_mappings)}"

        for m in claim_count_mappings:
            # 1. Source must strictly be Claims Volume.Claim Number
            assert m.source_table == "Claims Volume", f"Claim Count for {m.target_table} incorrectly attributed to {m.source_table}"
            assert m.source_attribute == "Claim Number", f"Claim Count for {m.target_table} incorrectly attributed to attribute {m.source_attribute}"
            assert m.transformation == "Aggregation"
            assert "distinct" in m.transformation_logic.lower()

            # 2. Claim Payments and Claim Diary Notes must NOT be listed
            assert m.source_table != "Claim Payments"
            assert m.source_table != "Claim Diary Notes"

    def test_aging_bucket_lineage(self):
        """Verify Aging Bucket derives from Last Activity Date with correct null/banding logic and NO 'null -> 0'."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        aging_mappings = [m for m in sttm.mappings if m.target_attribute == "Aging Bucket"]
        assert len(aging_mappings) == 1, f"Expected 1 Aging Bucket mapping, got {len(aging_mappings)}"
        
        m = aging_mappings[0]
        assert m.source_table == "Claim Diary Notes"
        assert m.source_attribute == "Last Activity Date"
        assert m.transformation == "Derived Calculation"
        assert "No Diary Activity" in m.transformation_logic
        assert "90+ Days" in m.transformation_logic
        assert "0-30 Days" in m.transformation_logic
        
        # Explicit check: DO NOT state or imply "null -> 0"
        assert "defaulting null/missing values in [days since last activity] to 0" not in m.transformation_logic.lower()
        assert "defaulted to 0" not in m.transformation_logic.lower()

    def test_quarterly_status_crosstab_dual_lineage(self):
        """Verify status-specific CrossTab columns receive both Claim Number (measure) and Claim Status (pivot header) dependencies."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        qs_mappings = [m for m in sttm.mappings if "QuarterSummary" in m.target_table or "Quarterly Volume" in m.target_table]
        assert len(qs_mappings) >= 5

        # Check Quarter End Date grouping key
        qed_mappings = [m for m in qs_mappings if m.target_attribute == "Quarter End Date"]
        assert len(qed_mappings) == 1
        assert qed_mappings[0].source_table == "Claims Volume"
        assert qed_mappings[0].source_attribute == "Quarter End Date"
        assert qed_mappings[0].transformation == "Pivot / Reshape"

        # Check status columns: Preclaim, Active_Pending, Approved, Stable_and_Mature
        for status_col in ["Preclaim", "Active_Pending", "Approved", "Stable_and_Mature"]:
            col_mappings = [m for m in qs_mappings if m.target_attribute == status_col]
            assert len(col_mappings) == 2, f"Expected 2 dual source mappings for {status_col}, got {len(col_mappings)}"
            
            source_attrs = {cm.source_attribute for cm in col_mappings}
            assert "Claim Number" in source_attrs, f"{status_col} missing Claim Number measure dependency"
            assert "Claim Status" in source_attrs, f"{status_col} missing Claim Status categorical dependency"

            for cm in col_mappings:
                assert cm.source_table == "Claims Volume"
                assert cm.transformation == "Pivot / Reshape"

    def test_payment_lineage(self):
        """Verify Total Paid in Product Type and State outputs traces to Claim Payments.Payment Amount via intermediate rollup."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        paid_mappings = [
            m for m in sttm.mappings if "paid" in m.target_attribute.lower()
        ]
        assert len(paid_mappings) >= 2

        for m in paid_mappings:
            assert m.source_table == "Claim Payments"
            assert m.source_attribute == "Payment Amount"
            assert m.transformation == "Aggregation"
            assert "SUM" in m.transformation_logic
            assert "claim-level" in m.transformation_logic.lower() or "payment" in m.transformation_logic.lower()

    def test_no_false_upstream_attribution(self):
        """Verify participating datasets are not falsely attributed to unrelated target fields."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        wf = parse_workflow(wf_path)
        g = build_graph(wf)
        order = execution_order(g)
        bs = generate_business_summary(wf, g, order)
        sttm = extract_sttm(wf, g, bs)

        detail_mappings = [m for m in sttm.mappings if "Detail" in m.target_table]
        # Detail extract must ONLY come from Claims Volume
        for m in detail_mappings:
            assert m.source_table == "Claims Volume", f"Detail attribute {m.target_attribute} falsely attributed to {m.source_table}"

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
