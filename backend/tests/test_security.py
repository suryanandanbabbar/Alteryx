"""Tests for security constraints on upload and package processing."""

import io
import zipfile
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_zip_path_traversal_attack_blocked():
    # Create malicious ZIP attempting directory traversal
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../evil.yxmd", b"<AlteryxDocument/>")
    pkg_bytes = buf.getvalue()

    resp = client.post(
        "/api/upload",
        files={"file": ("malicious.yxwz", pkg_bytes, "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "SECURITY_PATH_TRAVERSAL"


def test_empty_file_upload_rejected():
    resp = client.post(
        "/api/upload",
        files={"file": ("empty.yxmd", b"", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_non_workflow_binary_rejected():
    resp = client.post(
        "/api/upload",
        files={"file": ("binary.yxmd", b"\x7fELF\x02\x01\x01\x00", "application/octet-stream")},
    )
    assert resp.status_code == 422
