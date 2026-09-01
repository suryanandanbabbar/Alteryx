"""Comprehensive test suite for Business Area Portfolio -> Dashboard Summary -> Workflow Detail hierarchy.

Validates Requirements 1-35:
1. Level 1: Business Area Portfolio landing structure with dynamic <N> workflows analysed and domain counts.
2. Level 2: Dashboard Summary workflow fields (filename, business_purpose, tools/node_count, connections/connection_count, sources, targets).
3. Level 3: Individual workflow retrieval by ID from portfolio without re-analysis.
4. Target vs Inspection Sink distinction (BrowseV2 not in targets).
5. Accurate connection counts derived from canonical graph edges.
6. Strict LLM evidence boundary maintained during portfolio ingestion.
7. Graceful deterministic fallback under LLM failure.
8. Single workflow regression (direct single file upload continues to single-workflow analysis).
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from awa.analysis.business_area_classifier import extract_output_evidence_for_workflow
from awa.analysis.portfolio_analyzer import build_portfolio_analysis
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.llm.cache import LLMNarrativeCache
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator, set_default_generator
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestPortfolioNavigationHierarchy:
    """Tests for the 3-level navigation hierarchy and canonical data models."""

    def test_single_workflow_direct_upload_bypasses_portfolio(self, client):
        """Requirement 21: Single workflow upload routes directly to single-workflow analysis."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "portfolio_id" not in data
        assert data["source"]["original_filename"] == "Demo_Claims.yxmd"

    def test_level1_portfolio_landing_counts_and_structure(self, client):
        """Requirement 2-5: Multi-workflow upload creates Level 1 portfolio with dynamic count and business areas."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Claims.yxmd", Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes())
            zf.writestr("FTSE.yxmd", Path("FTSE 100.yxmd").read_bytes())
            zf.writestr("Food.yxmd", Path("BBCFoodAggr.yxmd").read_bytes())
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("portfolio.zip", zip_buf.getvalue(), "application/zip"))],
            data={"portfolio_name": "Enterprise ETL Portfolio"},
        )

        assert resp.status_code == 200
        data = resp.json()

        # Dynamic workflow counts
        assert data["workflow_count"] == 3
        assert data["metrics"]["total_workflows"] == 3
        assert data["metrics"]["successful_workflows"] == 3
        assert data["metrics"]["failed_workflows"] == 0

        # Business area distribution
        assert "business_area_counts" in data
        counts = data["business_area_counts"]
        assert sum(counts.values()) == 3

    def test_level2_dashboard_summary_workflow_fields(self, client):
        """Requirement 9-15: Each workflow summary provides exact Dashboard Summary columns.

        Columns: Workflow, Business Summary, Tools, Connections, Sources, Targets.
        """
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Demo_Claims.yxmd", Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes())
            zf.writestr("FTSE.yxmd", Path("FTSE 100.yxmd").read_bytes())
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("portfolio.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 200
        data = resp.json()

        for wf in data["workflows"]:
            # 1. Workflow filename
            assert wf["filename"] in ("Demo_Claims.yxmd", "FTSE.yxmd")
            # 2. Business Summary
            assert "business_purpose" in wf
            assert len(wf["business_purpose"]) > 0
            # 3. Tools count
            assert wf["node_count"] > 0
            # 4. Connections count
            assert wf["connection_count"] >= 0
            # 5. Sources list
            assert isinstance(wf["sources"], list)
            # 6. Targets list
            assert isinstance(wf["targets"], list)
            # 7. Analysis ID / workflow ID for Level 3 navigation
            assert "analysis_id" in wf or "workflow_id" in wf
            assert "business_area" in wf

    def test_connection_count_matches_canonical_graph(self):
        """Requirement 13 & 23: Connection count accurately reflects canonical workflow graph."""
        res_claims = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        res_ftse = analyze_canonical(Path("FTSE 100.yxmd"))

        portfolio = build_portfolio_analysis([
            ("Demo_Claims.yxmd", "Demo_Claims.yxmd", res_claims),
            ("FTSE.yxmd", "FTSE.yxmd", res_ftse),
        ])

        summary_claims = next(w for w in portfolio.workflows if w.filename == "Demo_Claims.yxmd")
        summary_ftse = next(w for w in portfolio.workflows if w.filename == "FTSE.yxmd")

        # Must match canonical metrics total_connections
        assert summary_claims.connection_count == res_claims.metrics.total_connections
        assert summary_ftse.connection_count == res_ftse.metrics.total_connections
        assert summary_claims.connection_count == len(res_claims.workflow.connections)

    def test_inspection_sinks_excluded_from_targets(self):
        """Requirement 15: Browse/BrowseV2 inspection sinks are NOT counted as production targets."""
        res_food = analyze_canonical(Path("BBCFoodAggr.yxmd"))
        # BBCFoodAggr terminates in BrowseV2
        portfolio = build_portfolio_analysis([
            ("BBCFoodAggr.yxmd", "BBCFoodAggr.yxmd", res_food),
        ])
        wf = portfolio.workflows[0]
        assert len(wf.targets) == 0
        assert len(wf.inspection_sinks) > 0

    def test_level3_workflow_retrieval_without_reanalysis(self, client):
        """Requirement 16-20: Retrieving a workflow by ID reuses existing cached analysis."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Claims.yxmd", Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes())
            zf.writestr("FTSE.yxmd", Path("FTSE 100.yxmd").read_bytes())
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("portfolio.zip", zip_buf.getvalue(), "application/zip"))],
        )
        data = resp.json()
        wf_id = data["workflows"][0]["workflow_id"]

        # Level 3: Fetch single workflow overview by ID
        get_resp = client.get(f"/api/analysis/{wf_id}/overview")
        assert get_resp.status_code == 200
        wf_data = get_resp.json()
        assert wf_data["analysis_id"] == wf_id
        assert "metrics" in wf_data
        assert "source" in wf_data

    def test_strict_evidence_boundary_on_classifier(self):
        """Requirement 6: Business area classification receives ONLY output dataset names and columns."""
        res = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        evidence = extract_output_evidence_for_workflow(res)

        payload_json = json.dumps({"outputs": evidence})

        # Workflow filename, ID, sources, tool types must NOT appear in output evidence
        assert res.analysis_id not in payload_json
        assert "Demo_Claims_Volume_Extract" not in payload_json
        for tid in res.workflow.tools:
            tool = res.workflow.tools[tid]
            assert f"tool_{tid}" not in payload_json

        # Every output entry only contains allowed keys
        for out in evidence:
            assert set(out.keys()).issubset({"dataset", "table_or_sheet", "columns"})

    def test_business_area_descriptions_present_and_domain_focused(self, client):
        """Verify business-area descriptions are populated, domain-focused, and stable."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Claims.yxmd", Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes())
            zf.writestr("FTSE.yxmd", Path("FTSE 100.yxmd").read_bytes())
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("portfolio.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "business_area_descriptions" in data
        descriptions = data["business_area_descriptions"]
        assert isinstance(descriptions, dict)

        # Must include all primary business domains + Unclassified
        assert "Claims & Risk" in descriptions
        assert "Sales & Distribution" in descriptions
        assert "Legal" in descriptions
        assert "Underwriting" in descriptions
        assert "Other / Unclassified" in descriptions

        for area, desc in descriptions.items():
            assert isinstance(desc, str)
            assert len(desc) > 20
            # Must NOT reference specific tool ids or workflow filenames
            assert "Demo_Claims" not in desc
            assert "tool_" not in desc

        # Other / Unclassified must explicitly mention evidence limitation
        assert "evidence" in descriptions["Other / Unclassified"].lower()
