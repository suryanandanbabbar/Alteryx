"""Unit and API tests for application configuration."""

import pytest
from fastapi.testclient import TestClient

from backend.app.config import (
    validate_code_based_workflows_url,
    validate_kpi_ontology_bank_url,
    Settings,
)
from backend.app.main import app

client = TestClient(app)


def test_validate_kpi_ontology_bank_url_valid():
    assert validate_kpi_ontology_bank_url("https://kpi-bank.example.com") == "https://kpi-bank.example.com"
    assert validate_kpi_ontology_bank_url("http://localhost:8080/kpi") == "http://localhost:8080/kpi"
    assert validate_kpi_ontology_bank_url(None) is None
    assert validate_kpi_ontology_bank_url("") is None
    assert validate_kpi_ontology_bank_url("   ") is None


def test_validate_kpi_ontology_bank_url_invalid():
    with pytest.raises(ValueError, match="scheme"):
        validate_kpi_ontology_bank_url("ftp://kpi-bank.example.com")

    with pytest.raises(ValueError, match="scheme"):
        validate_kpi_ontology_bank_url("javascript:alert(1)")

    with pytest.raises(ValueError, match="hostname"):
        validate_kpi_ontology_bank_url("http://")


def test_api_config_endpoint():
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "code_based_workflows_url" in data
    assert "kpi_ontology_bank_url" in data
