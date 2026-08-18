"""Tests for security constraints on upload and package processing."""

import io
import zipfile
from unittest.mock import patch
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


def test_oversized_upload_rejected():
    with patch("backend.app.api.upload.settings.max_upload_bytes", 100):
        large_payload = b"A" * 200
        resp = client.post(
            "/api/upload",
            files={"file": ("large.yxmd", large_payload, "application/octet-stream")},
        )
        assert resp.status_code == 413
        assert resp.json()["detail"]["code"] == "FILE_TOO_LARGE"
