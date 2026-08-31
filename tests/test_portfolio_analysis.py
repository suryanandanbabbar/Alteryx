"""Comprehensive test suite for Multi-Workflow Portfolio Analysis and ETL Rationalisation."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from awa.parser.xml_parser import parse_workflow
from awa.graph.builder import build_graph
from awa.analysis.workflow_analyzer import analyze_canonical
from awa.model.portfolio import PortfolioAnalysis, WorkflowRelationship
from awa.analysis.portfolio_analyzer import (
    build_portfolio_analysis,
    enrich_portfolio_with_llm,
    compute_multi_signal_relationship,
)
from awa.llm.client import FakeLLMClient
from awa.llm.generator import LLMNarrativeGenerator, set_default_generator
from awa.llm.cache import LLMNarrativeCache
from backend.app.main import app
from backend.app.services.portfolio_service import (
    extract_workflows_from_zip,
    process_portfolio_uploads,
)
from backend.app.services.storage import get_storage


@pytest.fixture
def client():
    return TestClient(app)


class TestPortfolioAnalysis:
    """Test suite covering ingestion, invariants, multi-signal similarity, and partial failures."""

    def test_single_workflow_regression_upload(self, client):
        """Single YXMD upload must preserve exact existing single-workflow response."""
        wf_path = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd")
        with open(wf_path, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("Demo_Claims.yxmd", f, "application/xml")})

        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "portfolio_id" not in data
        assert data["source"]["original_filename"] == "Demo_Claims.yxmd"
        assert data["metrics"]["total_nodes"] > 0

    def test_empty_folder_rejection(self, client):
        """Empty folder or upload with zero valid workflows returns clear 400 error."""
        # Create an empty zip representing an empty folder
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            pass  # no files
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("empty.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "NO_WORKFLOWS_FOUND"

    def test_folder_with_mixed_files_discovery(self, client):
        """Folder with mixed valid and unsupported files processes only valid YXMD files."""
        wf_bytes = Path("FTSE 100.yxmd").read_bytes()
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Workflows/FTSE.yxmd", wf_bytes)
            zf.writestr("Workflows/readme.txt", "documentation notes")
            zf.writestr("Workflows/logo.png", b"\x89PNG\r\n\x1a\nfake")
        zip_buf.seek(0)

        # Single workflow in zip -> returns single-workflow analysis
        resp = client.post(
            "/api/upload",
            files={"file": ("workflows.zip", zip_buf.getvalue(), "application/zip")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "portfolio_id" not in data

    def test_multi_workflow_zip_portfolio_creation(self, client):
        """ZIP containing multiple workflows creates a portfolio with distinct workflows."""
        claims_bytes = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes()
        ftse_bytes = Path("FTSE 100.yxmd").read_bytes()

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Claims/Extract.yxmd", claims_bytes)
            zf.writestr("Finance/FTSE.yxmd", ftse_bytes)
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("bundle.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "portfolio_id" in data
        assert data["workflow_count"] == 2
        assert len(data["workflows"]) == 2

        # Verify relative paths preserved
        rel_paths = {w["relative_path"] for w in data["workflows"]}
        assert "Claims/Extract.yxmd" in rel_paths
        assert "Finance/FTSE.yxmd" in rel_paths

        # Verify individual workflows can be accessed via analysis endpoint
        for w in data["workflows"]:
            wid = w["workflow_id"]
            wf_resp = client.get(f"/api/analysis/{wid}/overview")
            assert wf_resp.status_code == 200

    def test_partial_failure_handling(self, client):
        """Invalid workflow does not crash the portfolio; reports success and failed counts."""
        valid_bytes = Path("FTSE 100.yxmd").read_bytes()
        corrupt_bytes = b"<?xml version='1.0'?><CorruptedXml><UnclosedTag>"

        files = [
            ("files", ("FTSE.yxmd", valid_bytes, "application/xml")),
            ("files", ("Corrupt.yxmd", corrupt_bytes, "application/xml")),
        ]
        resp = client.post("/api/portfolio/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()

        assert data["workflow_count"] == 2
        assert data["metrics"]["successful_workflows"] == 1
        assert data["metrics"]["failed_workflows"] == 1

        failed_wfs = [w for w in data["workflows"] if w["status"] == "FAILED"]
        assert len(failed_wfs) == 1
        assert failed_wfs[0]["filename"] == "Corrupt.yxmd"
        assert failed_wfs[0]["error_message"] is not None

    def test_actual_filenames_preserved_in_evidence(self):
        """Authoritative source and target filenames are preserved; *Unknown strictly purged."""
        claims_res = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        ftse_res = analyze_canonical(Path("FTSE 100.yxmd"))

        portfolio = build_portfolio_analysis([
            ("Demo_Claims.yxmd", "Claims/Demo_Claims.yxmd", claims_res),
            ("FTSE.yxmd", "Finance/FTSE.yxmd", ftse_res),
        ])

        assert portfolio.workflow_count == 2
        claims_summary = next(w for w in portfolio.workflows if w.filename == "Demo_Claims.yxmd")
        ftse_summary = next(w for w in portfolio.workflows if w.filename == "FTSE.yxmd")

        # Physical source filenames
        assert any("Claims_Volume_Extract_Demo.xlsx" in s for s in claims_summary.sources)
        assert any("Policy_Master_Demo.xlsx" in s for s in claims_summary.sources)
        assert any("Claims_Aging_Risk_Demo_Output.xlsx" in t for t in claims_summary.targets)
        assert "FTSEData.tde" in ftse_summary.targets

        # Zero *Unknown in sources or targets
        for w in portfolio.workflows:
            for s in w.sources:
                assert "*unknown" not in s.lower()
                assert not s.startswith("*")
            for t in w.targets:
                assert "*unknown" not in t.lower()
                assert not t.startswith("*")

    def test_browse_sink_distinction_constraint2(self):
        """Constraint 2: BrowseV2 is an inspection sink, not a production deliverable."""
        bbc_res = analyze_canonical(Path("BBCFoodAggr.yxmd"))
        portfolio = build_portfolio_analysis([
            ("BBCFoodAggr.yxmd", "BBCFoodAggr.yxmd", bbc_res),
        ])

        summary = portfolio.workflows[0]
        assert summary.target_count == 0  # 0 production deliverables
        assert len(summary.inspection_sinks) > 0  # Contains inspection sinks
        assert any("Browse" in s for s in summary.inspection_sinks)

        # Rationalisation candidate generated for review/inspection asset
        assert any(c.recommendation_type == "REVIEW" for c in portfolio.rationalisation_candidates)

    def test_multi_signal_similarity_constraint1(self):
        """Constraint 1: Similarity combines independent signals and separates evidence from interpretation."""
        claims_res1 = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        # Synthetic copy of claims workflow
        claims_res2 = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))

        portfolio = build_portfolio_analysis([
            ("Claims_A.yxmd", "v1/Claims_A.yxmd", claims_res1),
            ("Claims_B.yxmd", "v2/Claims_B.yxmd", claims_res2),
        ])

        assert len(portfolio.relationships) > 0
        rel = portfolio.relationships[0]

        # Invariant: Evidence is auditable and separate from LLM reasoning
        signals = rel.deterministic_signals
        assert len(signals.shared_sources) > 0
        assert len(signals.shared_targets) > 0
        assert signals.tool_sequence_similarity == 1.0
        assert signals.graph_topology_similarity == 1.0
        assert signals.composite_score >= 0.90
        assert rel.relationship_type == "DUPLICATE_CANDIDATE"

        # Evidence statements generated auditably
        assert any("Shares" in ev for ev in rel.evidence)
        assert any("tool sequence alignment" in ev for ev in rel.evidence)

    def test_portfolio_llm_qualification_and_hallucination_resistance(self):
        """Portfolio LLM qualification enhances reasoning while rejecting hallucinated workflows."""
        claims_res = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        ftse_res = analyze_canonical(Path("FTSE 100.yxmd"))

        portfolio = build_portfolio_analysis([
            ("Demo_Claims.yxmd", "Claims/Demo_Claims.yxmd", claims_res),
            ("FTSE.yxmd", "Finance/FTSE.yxmd", ftse_res),
        ])

        wid_claims = claims_res.analysis_id
        wid_ftse = ftse_res.analysis_id

        # Mock LLM response with 1 valid relationship qualification and 1 hallucinated ID
        mock_response = {
            "qualified_relationships": [
                {
                    "workflow_a_id": wid_claims,
                    "workflow_b_id": wid_ftse,
                    "relationship_type": "STRUCTURAL_SIMILARITY",
                    "reasoning": "Distinct enterprise domains but share analytical pipeline structure.",
                    "confidence": "MEDIUM",
                },
                {
                    "workflow_a_id": "fake_nonexistent_workflow_id",
                    "workflow_b_id": wid_ftse,
                    "relationship_type": "DUPLICATE_CANDIDATE",
                    "reasoning": "Fabricated relationship that must be rejected.",
                    "confidence": "HIGH",
                },
            ],
            "rationalisation_recommendations": [
                {
                    "workflow_ids": [wid_claims],
                    "recommendation_type": "REVIEW",
                    "reasoning": "Verify claim categorization mappings.",
                    "confidence": "HIGH",
                },
                {
                    "workflow_ids": ["hallucinated_wid"],
                    "recommendation_type": "CONSOLIDATE",
                    "reasoning": "Hallucinated entry.",
                    "confidence": "HIGH",
                },
            ],
        }

        fake_client = FakeLLMClient(default_response=json.dumps(mock_response))
        generator = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
        set_default_generator(generator)

        # Manually add a structural relationship if not present so LLM can qualify it
        if not portfolio.relationships:
            from awa.model.portfolio import DeterministicSignals
            portfolio.relationships.append(
                WorkflowRelationship(
                    workflow_a_id=wid_claims,
                    workflow_a_name="Demo_Claims.yxmd",
                    workflow_b_id=wid_ftse,
                    workflow_b_name="FTSE.yxmd",
                    relationship_type="STRUCTURAL_SIMILARITY",
                    deterministic_signals=DeterministicSignals(composite_score=0.5),
                    evidence=["Structural comparison"],
                )
            )

        enriched = enrich_portfolio_with_llm(portfolio)

        # 1. Valid relationship received LLM reasoning
        matched_rel = next(
            r for r in enriched.relationships
            if (r.workflow_a_id == wid_claims and r.workflow_b_id == wid_ftse)
        )
        assert matched_rel.llm_reasoning == "Distinct enterprise domains but share analytical pipeline structure."

        # 2. Hallucinated workflow ID was rejected
        assert not any("fake_nonexistent_workflow_id" in (r.workflow_a_id, r.workflow_b_id) for r in enriched.relationships)
        assert not any("hallucinated_wid" in c.workflow_ids for c in enriched.rationalisation_candidates)

    def test_state_and_navigation_preservation(self, client):
        """Verify portfolio state is preserved and workflows can be retrieved without re-upload."""
        claims_bytes = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes()
        ftse_bytes = Path("FTSE 100.yxmd").read_bytes()

        files = [
            ("files", ("Claims.yxmd", claims_bytes, "application/xml")),
            ("files", ("FTSE.yxmd", ftse_bytes, "application/xml")),
        ]
        resp = client.post("/api/portfolio/upload", files=files)
        assert resp.status_code == 200
        portfolio_data = resp.json()
        pid = portfolio_data["portfolio_id"]

        # 1. Retrieve portfolio by ID
        get_p_resp = client.get(f"/api/portfolio/{pid}")
        assert get_p_resp.status_code == 200
        assert get_p_resp.json()["portfolio_id"] == pid

        # 2. Retrieve individual workflow from portfolio
        wid = portfolio_data["workflows"][0]["workflow_id"]
        wf_resp = client.get(f"/api/portfolio/{pid}/workflow/{wid}")
        assert wf_resp.status_code == 200
        assert wf_resp.json()["analysis_id"] == wid

    def test_no_redundant_individual_llm_rerun_constraint3(self):
        """Constraint 3: Portfolio analysis strictly consumes existing workflow results without re-running individual LLMs."""
        call_log: list[str] = []

        def tracking_generator(sys_prompt: str, user_prompt: str) -> str:
            call_log.append(sys_prompt[:60])
            return json.dumps({
                "qualified_relationships": [],
                "rationalisation_recommendations": [],
            })

        fake_client = FakeLLMClient(generator_fn=tracking_generator)
        gen = LLMNarrativeGenerator(client=fake_client, cache=LLMNarrativeCache())
        set_default_generator(gen)

        # Existing individual results
        claims_res = analyze_canonical(Path("Demo_Claims_Volume_Extract_reconstructed.yxmd"))
        ftse_res = analyze_canonical(Path("FTSE 100.yxmd"))

        call_log.clear()

        # Build portfolio and run portfolio LLM
        portfolio = build_portfolio_analysis([
            ("Demo_Claims.yxmd", "Claims/Demo_Claims.yxmd", claims_res),
            ("FTSE.yxmd", "Finance/FTSE.yxmd", ftse_res),
        ])
        enrich_portfolio_with_llm(portfolio)

        # Invariant: Only the portfolio rationalisation LLM is called (at most 1 call), NOT individual workflow LLMs
        for call in call_log:
            assert "You are a Principal Enterprise Data Architect" in call
            # Never individual workflow prompts
            assert "tool specifications" not in call.lower()
            assert "source-to-target" not in call.lower()

    def test_case_insensitive_workflow_extensions(self, client):
        """Case-insensitive workflow extensions (.YXMD, .YXWZ, .XML) are recognised and accepted."""
        wf_bytes = Path("FTSE 100.yxmd").read_bytes()
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("WORKFLOWS/A.YXMD", wf_bytes)
            zf.writestr("WORKFLOWS/B.YXWZ", wf_bytes)
            zf.writestr("WORKFLOWS/C.XML", wf_bytes)
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("archive.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_count"] == 3
        filenames = {w["filename"] for w in data["workflows"]}
        assert "A.YXMD" in filenames
        assert "B.YXWZ" in filenames
        assert "C.XML" in filenames

    def test_folder_with_one_workflow_and_unsupported_files(self, client):
        """Folder containing 1 workflow and multiple unsupported files treats input as single workflow."""
        wf_bytes = Path("Demo_Claims_Volume_Extract_reconstructed.yxmd").read_bytes()
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("ETL/Claims.yxmd", wf_bytes)
            zf.writestr("ETL/README.md", "# ETL Documentation")
            zf.writestr("ETL/notes.txt", "some notes")
            zf.writestr("ETL/image.png", b"\x89PNG\r\n\x1a\nfake")
            zf.writestr("ETL/output.xlsx", b"PK\x03\x04fake_excel")
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("ETL.zip", zip_buf.getvalue(), "application/zip"))],
        )
        # Exactly 1 valid workflow discovered -> returns AnalysisOverviewDTO (single-workflow mode)
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis_id" in data
        assert "portfolio_id" not in data
        assert data["source"]["original_filename"] == "Claims.yxmd"

    def test_nested_folder_preserves_distinct_identities(self, client):
        """Identically named workflows in different subdirectories preserve relative paths and remain distinct."""
        wf_bytes = Path("FTSE 100.yxmd").read_bytes()
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("Sales/A.yxmd", wf_bytes)
            zf.writestr("Finance/A.yxmd", wf_bytes)
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("Workflows.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_count"] == 2

        rel_paths = {w["relative_path"] for w in data["workflows"]}
        assert "Sales/A.yxmd" in rel_paths
        assert "Finance/A.yxmd" in rel_paths

        # Distinct workflow IDs generated
        wf_ids = [w["workflow_id"] for w in data["workflows"]]
        assert len(set(wf_ids)) == 2

    def test_empty_folder_with_only_unsupported_files_rejected(self, client):
        """Folder containing only unsupported files returns 400 error without calling analysis."""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("ETL/README.md", "# Readme")
            zf.writestr("ETL/data.csv", "a,b,c\n1,2,3")
            zf.writestr("ETL/notes.txt", "notes")
        zip_buf.seek(0)

        resp = client.post(
            "/api/portfolio/upload",
            files=[("files", ("ETL.zip", zip_buf.getvalue(), "application/zip"))],
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["code"] == "NO_WORKFLOWS_FOUND"

