"""Unit tests for backend application configuration, .env loading, and public config endpoint."""

import os
import pytest
from fastapi.testclient import TestClient
from backend.app.config import Settings, validate_code_based_workflows_url, get_settings, _find_project_dotenv, _load_dotenv_if_available
from backend.app.main import app
from backend.app.models.schemas import AppConfigDTO


def test_validate_code_based_workflows_url_valid_https():
    url = "  https://code-workflows.example.corp/dashboard?env=prod  "
    result = validate_code_based_workflows_url(url)
    assert result == "https://code-workflows.example.corp/dashboard?env=prod"


def test_validate_code_based_workflows_url_valid_http():
    url = "http://localhost:8080/app"
    result = validate_code_based_workflows_url(url)
    assert result == "http://localhost:8080/app"


def test_validate_code_based_workflows_url_none_and_empty():
    assert validate_code_based_workflows_url(None) is None
    assert validate_code_based_workflows_url("") is None
    assert validate_code_based_workflows_url("   ") is None


def test_validate_code_based_workflows_url_malformed():
    with pytest.raises(ValueError, match="Only 'http' and 'https' are allowed"):
        validate_code_based_workflows_url("ftp://ftp.example.com")

    with pytest.raises(ValueError, match="Only 'http' and 'https' are allowed"):
        validate_code_based_workflows_url("javascript:alert(1)")

    with pytest.raises(ValueError, match="Only 'http' and 'https' are allowed"):
        validate_code_based_workflows_url("data:text/html;base64,PHNjcmlwdD4=")

    with pytest.raises(ValueError, match="Only 'http' and 'https' are allowed"):
        validate_code_based_workflows_url("file:///etc/passwd")

    with pytest.raises(ValueError, match="Only 'http' and 'https' are allowed"):
        validate_code_based_workflows_url("not_a_url")

    with pytest.raises(ValueError, match="A valid hostname is required"):
        validate_code_based_workflows_url("https://")


def test_settings_env_loading(monkeypatch):
    monkeypatch.setenv("CODE_BASED_WORKFLOWS_URL", "https://configured-app.example.com")
    custom_settings = get_settings()
    assert custom_settings.code_based_workflows_url == "https://configured-app.example.com"


def test_settings_awa_prefix_compatibility(monkeypatch):
    monkeypatch.delenv("CODE_BASED_WORKFLOWS_URL", raising=False)
    monkeypatch.setenv("AWA_CODE_BASED_WORKFLOWS_URL", "https://awa-prefix-app.example.com")
    custom_settings = get_settings()
    assert custom_settings.code_based_workflows_url == "https://awa-prefix-app.example.com"


def test_settings_missing_env(monkeypatch):
    monkeypatch.delenv("CODE_BASED_WORKFLOWS_URL", raising=False)
    monkeypatch.delenv("AWA_CODE_BASED_WORKFLOWS_URL", raising=False)
    # Instantiate Settings directly without env vars
    s = Settings(code_based_workflows_url=None)
    assert s.code_based_workflows_url is None


def test_dotenv_loading_and_precedence(tmp_path, monkeypatch):
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text("CODE_BASED_WORKFLOWS_URL=https://from-dotenv.example.com\n")

    # When not set in process environment, .env should populate it
    monkeypatch.delenv("CODE_BASED_WORKFLOWS_URL", raising=False)
    monkeypatch.delenv("AWA_CODE_BASED_WORKFLOWS_URL", raising=False)

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(env_file), override=False)
    assert os.getenv("CODE_BASED_WORKFLOWS_URL") == "https://from-dotenv.example.com"

    # Precedence test: explicit process environment overrides .env when override=False
    monkeypatch.setenv("CODE_BASED_WORKFLOWS_URL", "https://process-override.example.com")
    load_dotenv(dotenv_path=str(env_file), override=False)
    assert os.getenv("CODE_BASED_WORKFLOWS_URL") == "https://process-override.example.com"


def test_api_config_endpoint_configured(monkeypatch):
    monkeypatch.setenv("CODE_BASED_WORKFLOWS_URL", "https://api-test.example.com")
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["code_based_workflows_url"] == "https://api-test.example.com"
    # Ensure ONLY non-sensitive fields are returned in public config
    assert set(data.keys()) == {"code_based_workflows_url"}


def test_api_config_endpoint_unconfigured(monkeypatch):
    monkeypatch.delenv("CODE_BASED_WORKFLOWS_URL", raising=False)
    monkeypatch.delenv("AWA_CODE_BASED_WORKFLOWS_URL", raising=False)
    client = TestClient(app)
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "code_based_workflows_url" in data
    assert set(data.keys()) == {"code_based_workflows_url"}
