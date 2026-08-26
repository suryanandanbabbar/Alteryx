from pathlib import Path
import docx
import pytest

from awa.analysis.workflow_analyzer import analyze_workflow, analyze_canonical
from awa.model.workflow import Workflow, WorkflowMetadata
from awa.model.tool import Tool, Position, ToolConfiguration
from awa.model.connection import Connection
from awa.graph.builder import build_graph, execution_order
from awa.analysis.business_intelligence import generate_business_summary
from awa.generators.doc_builder import build_document_model
from awa.generators.docx_generator import generate_docx


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

        # 4. Report body sections present in Business Report
        assert "4. Source-to-Target Data Lineage" in full_text or "2. Business Process & Operational Deliverables" in full_text
        # 5. Omitted sections must be ABSENT from Business Report
        assert "Recommendations" not in full_text
        assert "Visual Workflow Graph" not in full_text
        assert "DAG Architecture" not in full_text
        assert "Step-by-Step Tool Specifications" not in full_text
        assert "Technical Configuration Appendix" not in full_text

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
        assert "Step-by-Step Tool Specifications" not in full_text
        assert "Technical Configuration Appendix" not in full_text

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
        assert "Recommendations" not in exec_text
        assert "Limitations" not in exec_text

        # Word count check (~100-350 words)
        words = len(exec_text.split())
        assert 100 <= words <= 350, f"Demo claims executive summary word count: {words}"

        # No raw tool IDs in Executive Summary
        assert "#1" not in exec_text
        assert "#39" not in exec_text

        # Verify body sections in Business Report
        assert "2. Business Process & Operational Deliverables" in full_text
        assert "2.1 Inputs & Upstream Dependencies" in full_text
        assert "2.2 Outputs & Business Reporting Deliverables" in full_text
        assert "2.3 Sequential Operational Stages" in full_text
        assert "3. Key Business Rules & Transformations" in full_text
        assert "4. Source-to-Target Data Lineage" in full_text
        assert "5. Visual Workflow Graph" not in full_text
        assert "DAG Architecture" not in full_text

        # Verify Technical sections are REMOVED from Business Report
        assert "Step-by-Step Tool Specifications" not in full_text
        assert "Technical Configuration Appendix" not in full_text

        # Verify specific business facts & real source filenames in body
        assert "Claims_Volume_Extract_Demo.xlsx" in full_text
        assert "Policy_Master_Demo.xlsx" in full_text
        assert "Claim_Payments_Demo.xlsx" in full_text
        assert "Claim_Diary_Notes_Demo.xlsx" in full_text
        assert "Claims_Volume_Extract_Demo.xlsx" in full_text
        assert "Output" in full_text or "Deliverables" in full_text

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
        assert "5. Visual Workflow Graph (DAG Architecture)" not in headings

        # Verify text between "1. Executive Summary" and the next major heading is non-empty
        in_exec = False
        exec_lines = []
        for p in doc.paragraphs:
            if p.text == "1. Executive Summary":
                in_exec = True
            elif p.text.startswith("2. ") or p.text.startswith("3. ") or p.text.startswith("4. "):
                in_exec = False
            if in_exec:
                exec_lines.append(p.text)

        exec_text = "\n".join(exec_lines)
        assert len(exec_text.split()) >= 100
        assert "Methods of Analysis" in exec_text
        assert "Findings" in exec_text
        assert "Conclusions" in exec_text
        assert "Recommendations" not in exec_text
        assert "Limitations" not in exec_text

    def test_technical_specifications_docx_generation(self, tmp_path: Path):
        """Test Technical Specifications DOCX generation and verify content and structure."""
        from awa.analysis.workflow_analyzer import analyze_canonical
        from awa.generators.doc_builder import build_document_model
        from awa.generators.docx_generator import generate_docx, generate_technical_specifications_docx

        canonical = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        doc_model = build_document_model(
            canonical.workflow,
            canonical.execution_order,
            canonical.translations,
            canonical.dag_layout,
            canonical.lineage_paths,
            business_summary=canonical.business_summary,
            analysis_id=canonical.analysis_id,
            graph=canonical.graph,
        )

        biz_file = tmp_path / "Business_Report.docx"
        tech_file = tmp_path / "Technical_Specifications.docx"

        generate_docx(doc_model, biz_file)
        generate_technical_specifications_docx(doc_model, tech_file)

        assert biz_file.exists()
        assert tech_file.exists()

        biz_full = self._extract_all_docx_text(biz_file)
        tech_full = self._extract_all_docx_text(tech_file)

        biz_exec = self._extract_executive_summary_text(biz_file)
        tech_exec = self._extract_executive_summary_text(tech_file)

        # 1. Executive Summary in Technical Specifications exactly matches Business Report
        assert biz_exec == tech_exec
        assert len(tech_exec.split()) >= 50

        # 2. Business Report excludes technical sections
        assert "Step-by-Step Tool Specifications" not in biz_full
        assert "Technical Configuration Appendix" not in biz_full

        # 3. Technical Specifications includes technical sections
        assert "2. Step-by-Step Tool Specifications" in tech_full
        assert "3. Technical Configuration Appendix" in tech_full
        assert "Business Action:" in tech_full
        assert "Technical Function:" in tech_full
        assert "Tool #1" in tech_full
        assert "Tool #8" in tech_full

        # 4. Technical Specifications does not contain Business Process, Rules, Lineage, or DAG
        assert "2. Business Process & Operational Deliverables" not in tech_full
        assert "3. Key Business Rules & Transformations" not in tech_full
        assert "4. Source-to-Target Data Lineage" not in tech_full
        assert "5. Visual Workflow Graph (DAG Architecture)" not in tech_full

    def test_download_endpoints_for_both_reports(self):
        """Verify download endpoints return valid DOCX files for both Business Report and Technical Specifications."""
        import io
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        analysis_id = resp.json()["analysis_id"]

        # 1. Business Report
        resp_biz = client.get(f"/api/download/{analysis_id}/docx")
        assert resp_biz.status_code == 200
        assert "Business_Report.docx" in resp_biz.headers.get("Content-Disposition", "")
        doc_biz = docx.Document(io.BytesIO(resp_biz.content))
        biz_headings = [p.text for p in doc_biz.paragraphs if p.style.name.startswith("Heading")]
        assert "1. Executive Summary" in biz_headings
        assert "2. Step-by-Step Tool Specifications" not in biz_headings

        # 2. Technical Specifications
        resp_tech = client.get(f"/api/download/{analysis_id}/technical-docx")
        assert resp_tech.status_code == 200
        assert "Technical_Specifications.docx" in resp_tech.headers.get("Content-Disposition", "")
        doc_tech = docx.Document(io.BytesIO(resp_tech.content))
        tech_headings = [p.text for p in doc_tech.paragraphs if p.style.name.startswith("Heading")]
        assert "1. Executive Summary" in tech_headings
        assert "2. Step-by-Step Tool Specifications" in tech_headings
        assert "3. Technical Configuration Appendix" in tech_headings

        # 3. ZIP bundle contains both
        resp_zip = client.get(f"/api/download/{analysis_id}/zip")
        assert resp_zip.status_code == 200
        import zipfile
        zf = zipfile.ZipFile(io.BytesIO(resp_zip.content))
        zip_names = zf.namelist()
        assert any("Business_Report.docx" in name for name in zip_names)
        assert any("Technical_Specifications.docx" in name for name in zip_names)

    def test_canonical_filename_extraction_windows_and_unix_paths(self, tmp_path: Path):
        """Test 1 & 2: Given Windows or Unix path, canonical filename is extracted without directories."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties><Configuration><File>C:\\Data\\Claim_Volume_Extract_Demo.xlsx|||Sheet1$</File></Configuration></Properties>
    </Node>
    <Node ToolID="2">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="150" /></GuiSettings>
      <Properties><Configuration><File>/data/claims/Policy_Master_Unix.xlsx</File></Configuration></Properties>
    </Node>
  </Nodes>
  <Connections />
</AlteryxDocument>"""
        wf_file = tmp_path / "test_paths.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        canonical = analyze_canonical(wf_file)
        inputs = canonical.business_summary.source_inputs

        assert len(inputs) == 2
        inp1 = next(i for i in inputs if i.tool_id == 1)
        inp2 = next(i for i in inputs if i.tool_id == 2)

        assert inp1.source_filename == "Claim_Volume_Extract_Demo.xlsx"
        assert inp2.source_filename == "Policy_Master_Unix.xlsx"

    def test_annotation_not_authoritative_for_source_filename(self, tmp_path: Path):
        """Test 3: Annotation text must not override or determine the real filename from XML config."""
        xml_content = """<?xml version="1.0"?>
<AlteryxDocument yxmdVer="2024.1">
  <Nodes>
    <Node ToolID="1">
      <GuiSettings Plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput"><Position x="50" y="50" /></GuiSettings>
      <Properties>
        <Configuration><File>C:\\Data\\Claim_Volume_Extract_Demo.xlsx|||Sheet1$</File></Configuration>
        <Annotation DisplayMode="0"><DefaultAnnotationText>Claims Volume</DefaultAnnotationText></Annotation>
      </Properties>
    </Node>
  </Nodes>
  <Connections />
</AlteryxDocument>"""
        wf_file = tmp_path / "test_annotation.yxmd"
        wf_file.write_text(xml_content, encoding="utf-8")

        canonical = analyze_canonical(wf_file)
        inp = canonical.business_summary.source_inputs[0]

        assert inp.source_filename == "Claim_Volume_Extract_Demo.xlsx"

    def test_overview_dto_contains_canonical_source_filenames(self):
        """Test 4: Overview DTO for Demo Claims workflow contains canonical source filenames."""
        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        data = resp.json()
        source_inputs = data["business_summary"]["source_inputs"]

        filenames = [si["source_filename"] for si in source_inputs]
        assert "Claims_Volume_Extract_Demo.xlsx" in filenames
        assert "Policy_Master_Demo.xlsx" in filenames
        assert "Claim_Payments_Demo.xlsx" in filenames
        assert "Claim_Diary_Notes_Demo.xlsx" in filenames

    def test_fully_llm_authored_business_report_integration(self, tmp_path: Path):
        """Test full LLM-authored report generation using MockLLMClient."""
        import json
        from awa.llm.client import MockLLMClient, set_default_llm_client
        from awa.llm.generator import LLMNarrativeGenerator, set_default_generator
        from awa.generators.doc_builder import build_document_model
        from awa.generators.docx_generator import generate_docx

        mock_report = {
            "workflow_title": "Automated Customer Sales Reporting Pipeline",
            "workflow_description": "Production ETL pipeline consolidating customer transactions",
            "executive_summary": "This automated data workflow ingests daily customer transactions and generates aggregated portfolio revenue summaries for management reporting.",
            "methods_of_analysis": "The process joins customer master attributes with transaction event records, applies business calculation formulas to compute tax and net amounts, filters active accounts, and aggregates metrics by product line.",
            "findings": [
                "Combines two primary enterprise datasets into a unified analytical base.",
                "Enforces data standardization through automated calculation and zero-fill rules.",
                "Branches transformed data into specialized reporting extracts.",
                "Relies on external file storage for source ingestion."
            ],
            "conclusions": "The workflow serves as a centralized transaction preparation pipeline delivering reconciled revenue metrics to business stakeholders.",
            "inputs": [
                {
                    "source_dataset": "customers.xlsx",
                    "business_role": "Customer master dimension table",
                    "source_format": "Excel Workbook",
                    "dependency_significance": "Mandatory primary reference dataset"
                },
                {
                    "source_dataset": "orders.csv",
                    "business_role": "Transactional order history feed",
                    "source_format": "CSV Data File",
                    "dependency_significance": "Daily transactional volume source"
                }
            ],
            "outputs": [
                {
                    "output_deliverable": "customer_totals.xlsx",
                    "what_it_represents": "Reconciled customer sales revenue summary",
                    "business_use": "Monthly commercial revenue audit",
                    "destination_format": "Excel Workbook"
                }
            ],
            "sequential_stages": [
                {
                    "stage_number": 1,
                    "stage_name": "Source Ingestion",
                    "description": "Loads customer master and order transaction files",
                    "operational_explanation": "Validates schema and parses columnar datatypes"
                },
                {
                    "stage_number": 2,
                    "stage_name": "Relational Join & Aggregation",
                    "description": "Joins orders to customer records and calculates totals",
                    "operational_explanation": "Executes inner join on customer_id and computes sum of amounts"
                },
                {
                    "stage_number": 3,
                    "stage_name": "Deliverable Export",
                    "description": "Exports finalized customer totals to Excel",
                    "operational_explanation": "Formats numeric columns and writes workbook"
                }
            ],
            "business_rules": [
                {
                    "business_rule": "Customer ID Reconciliation",
                    "category": "Integration",
                    "evidence_configuration": "customers.customer_id = orders.customer_id"
                },
                {
                    "business_rule": "Revenue Total Rollup",
                    "category": "Aggregation",
                    "evidence_configuration": "SUM(orders.amount) GROUP BY customer_id, name"
                }
            ],
            "lineage": [
                {
                    "source_datasets": "customers.xlsx + orders.csv",
                    "major_business_transformation": "Join customer profiles with orders, aggregate revenue, and sort descending",
                    "target_deliverable": "customer_totals.xlsx"
                }
            ]
        }

        mock_client = MockLLMClient(default_response=json.dumps(mock_report))
        mock_gen = LLMNarrativeGenerator(client=mock_client)
        set_default_llm_client(mock_client)
        set_default_generator(mock_gen)

        try:
            canonical = analyze_canonical("fixtures/joins/join_workflow.yxmd")
            doc_model = build_document_model(
                canonical.workflow,
                canonical.execution_order,
                canonical.translations,
                canonical.dag_layout,
                canonical.lineage_paths,
                business_summary=canonical.business_summary,
                analysis_id=canonical.analysis_id,
                graph=canonical.graph,
            )

            out_docx = tmp_path / "llm_business_report.docx"
            generate_docx(doc_model, out_docx)
            assert out_docx.exists()

            full_text = self._extract_all_docx_text(out_docx)
            exec_text = self._extract_executive_summary_text(out_docx)

            # 1. Section 1 Executive Summary populated from LLM
            assert "1. Executive Summary" in exec_text
            assert "Methods of Analysis" in exec_text
            assert "Findings" in exec_text
            assert "Conclusions" in exec_text
            assert "This automated data workflow ingests daily customer transactions" in exec_text
            assert "Combines two primary enterprise datasets into a unified analytical base" in exec_text
            assert "The workflow serves as a centralized transaction preparation pipeline" in exec_text

            # 2. Section 2 Inputs & Outputs populated from LLM
            assert "2. Business Process & Operational Deliverables" in full_text
            assert "2.1 Inputs & Upstream Dependencies" in full_text
            assert "customers.xlsx" in full_text
            assert "Customer master dimension table" in full_text
            assert "orders.csv" in full_text
            assert "Transactional order history feed" in full_text

            assert "2.2 Outputs & Business Reporting Deliverables" in full_text
            assert "customer_totals.xlsx" in full_text
            assert "Reconciled customer sales revenue summary" in full_text
            assert "Monthly commercial revenue audit" in full_text

            assert "2.3 Sequential Operational Stages" in full_text
            assert "Source Ingestion" in full_text
            assert "Relational Join & Aggregation" in full_text

            # 3. Section 3 Business Rules populated from LLM
            assert "3. Key Business Rules & Transformations" in full_text
            assert "Customer ID Reconciliation" in full_text
            assert "Revenue Total Rollup" in full_text

            # 4. Section 4 Lineage populated from LLM
            assert "4. Source-to-Target Data Lineage" in full_text
            assert "Join customer profiles with orders" in full_text

            # 5. Omitted sections are NOT present
            assert "Recommendations" not in full_text
            assert "Visual Workflow Graph" not in full_text
            assert "DAG Architecture" not in full_text
        finally:
            set_default_llm_client(None)
            set_default_generator(None)

    def test_no_claims_hardcoding_in_generic_uncontainerized_workflow(self, tmp_path: Path):
        """Verify that a generic workflow with no containers does NOT produce claims-demo stage names or descriptions."""
        wf = Workflow(
            metadata=WorkflowMetadata(name="Sales Inventory Sync", version="2023.2"),
            tools={
                1: Tool(
                    tool_id=1,
                    plugin="AlteryxBasePluginsGui.DbFileInput.DbFileInput",
                    tool_type="DbFileInput",
                    name="Input Inventory",
                    position=Position(0, 0),
                    configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "inventory.csv"}),
                ),
                2: Tool(
                    tool_id=2,
                    plugin="AlteryxBasePluginsGui.Filter.Filter",
                    tool_type="Filter",
                    name="Filter Active",
                    position=Position(100, 0),
                    configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"Expression": "[Active] == 1"}),
                ),
                3: Tool(
                    tool_id=3,
                    plugin="AlteryxBasePluginsGui.DbFileOutput.DbFileOutput",
                    tool_type="DbFileOutput",
                    name="Output Active Inventory",
                    position=Position(200, 0),
                    configuration=ToolConfiguration(raw_xml="<Configuration/>", parsed={"file_path": "active_inventory.csv"}),
                ),
            },
            connections=[
                Connection(origin_tool_id=1, origin_anchor="Output", destination_tool_id=2, destination_anchor="Input"),
                Connection(origin_tool_id=2, origin_anchor="True", destination_tool_id=3, destination_anchor="Input"),
            ],
        )

        graph = build_graph(wf)
        exec_order = execution_order(graph)
        bs = generate_business_summary(wf, graph, exec_order)

        doc_model = build_document_model(
            workflow=wf,
            execution_order=exec_order,
            translations={},
            dag_layout=None,
            lineage_paths=[],
            business_summary=bs,
            analysis_id="generic-test-1",
        )

        out_docx = tmp_path / "generic_report.docx"
        generate_docx(doc_model, out_docx)
        assert out_docx.exists()

        full_text = self._extract_all_docx_text(out_docx)

        # Prohibit claims-specific legacy stage names and descriptions
        forbidden_strings = [
            "Historical volume and team aggregations",
            "Cross-source data enrichment and calculations",
            "Publish analytical deliverables",
            "Business use: Not documented",
            "Recommendations",
            "Visual Workflow Graph",
            "DAG Architecture",
        ]
        for s in forbidden_strings:
            assert s not in full_text, f"Found forbidden legacy string in generic report: {s}"



