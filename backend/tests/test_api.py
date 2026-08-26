"""Backend integration tests for all API endpoints using FastAPI TestClient."""

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()


def test_upload_and_query_workflow():
    # 1. Upload simple_filter.yxmd
    with open("fixtures/basic/simple_filter.yxmd", "rb") as f:
        resp = client.post(
            "/api/upload",
            files={"file": ("simple_filter.yxmd", f, "application/octet-stream")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "analysis_id" in data
    aid = data["analysis_id"]
    assert data["metrics"]["total_nodes"] == 3
    assert data["metrics"]["total_connections"] == 2
    assert len(data["execution_order"]) == 3
    assert all(step.get("summary") for step in data["execution_order"])

    # 2. Query /api/analysis/{aid}/overview
    resp_ov = client.get(f"/api/analysis/{aid}/overview")
    assert resp_ov.status_code == 200
    ov_data = resp_ov.json()
    assert ov_data["analysis_id"] == aid
    assert all(step.get("summary") for step in ov_data["execution_order"])

    # 3. Query /api/analysis/{aid}/diagram
    resp_diag = client.get(f"/api/analysis/{aid}/diagram")
    assert resp_diag.status_code == 200
    diag_data = resp_diag.json()
    assert "<svg" in diag_data["svg"]
    assert len(diag_data["nodes"]) == 3
    assert all(node.get("summary") for node in diag_data["nodes"])

    # 4. Query /api/analysis/{aid}/json
    resp_json = client.get(f"/api/analysis/{aid}/json")
    assert resp_json.status_code == 200
    assert "workflow" in resp_json.json()

    # 5. Query /api/analysis/{aid}/python
    resp_py = client.get(f"/api/analysis/{aid}/python")
    assert resp_py.status_code == 200
    py_data = resp_py.json()
    assert "import pandas as pd" in py_data["code"]
    assert len(py_data["trace_map"]) == 3
    assert "pandas" in py_data["required_libraries"]

    # 6. Query /api/analysis/{aid}/diagnostics
    resp_d = client.get(f"/api/analysis/{aid}/diagnostics")
    assert resp_d.status_code == 200
    assert "diagnostics" in resp_d.json()

    # 7. Test Downloads
    # 7a. Business Report DOCX download
    resp_docx = client.get(f"/api/download/{aid}/docx")
    assert resp_docx.status_code == 200
    assert len(resp_docx.content) > 0
    assert "Business_Report.docx" in resp_docx.headers.get("Content-Disposition", "")

    # 7a2. Tool Specifications XLSX download
    resp_tool_xlsx = client.get(f"/api/download/{aid}/tool-specifications")
    assert resp_tool_xlsx.status_code == 200
    assert len(resp_tool_xlsx.content) > 0
    assert "Tool_Specifications.xlsx" in resp_tool_xlsx.headers.get("Content-Disposition", "")

    # 7b. SVG download
    resp_svg = client.get(f"/api/download/{aid}/svg")
    assert resp_svg.status_code == 200
    assert b"<svg" in resp_svg.content

    # 7c. JSON download
    resp_dl_json = client.get(f"/api/download/{aid}/json")
    assert resp_dl_json.status_code == 200
    assert len(resp_dl_json.content) > 0

    # 7d. Python download
    resp_dl_py = client.get(f"/api/download/{aid}/python")
    assert resp_dl_py.status_code == 200
    assert b"import pandas as pd" in resp_dl_py.content

    # 7e. ZIP download
    resp_zip = client.get(f"/api/download/{aid}/zip")
    assert resp_zip.status_code == 200
    assert resp_zip.content[:4] == b"PK\x03\x04"


def test_upload_invalid_xml():
    resp = client.post(
        "/api/upload",
        files={"file": ("invalid.xml", b"<xml>not an alteryx workflow</xml>", "application/xml")},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "UNRECOGNIZED_WORKFLOW_XML"


def test_nonexistent_analysis_404():
    resp = client.get("/api/analysis/non-existent-uuid/overview")
    assert resp.status_code == 404
