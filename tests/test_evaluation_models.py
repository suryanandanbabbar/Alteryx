"""Tests for deterministic Complexity and Criticality evaluation model specifications."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from awa.analysis.workflow_complexity import (
    COMPLEXITY_EVALUATION_FACTORS,
    COMPLEXITY_WEIGHTS,
    get_complexity_evaluation_model,
)
from awa.analysis.workflow_criticality import (
    CRITICALITY_EVALUATION_FACTORS,
    CRITICALITY_FACTOR_WEIGHT,
    OPERATIONAL_WEIGHT_TOTAL,
    TECHNICAL_WEIGHT_TOTAL,
    get_criticality_evaluation_model,
)
from backend.app.main import app


def test_get_evaluation_models_api_endpoint():
    """Verify GET /api/portfolio/evaluation-models returns authoritative model specifications."""
    client = TestClient(app)
    response = client.get("/api/portfolio/evaluation-models")
    assert response.status_code == 200, response.text
    data = response.json()

    assert "complexity" in data
    assert "criticality" in data

    # Complexity model validation
    complexity = data["complexity"]
    assert complexity["model_name"] == "Complexity Evaluation Model"
    assert complexity["total_weight_pct"] == 100
    assert len(complexity["factors"]) == 5

    complexity_weight_sum = sum(f["weight_pct"] for f in complexity["factors"])
    assert complexity_weight_sum == 100

    factor_map = {f["id"]: f for f in complexity["factors"]}
    assert factor_map["size"]["weight_pct"] == 20
    assert factor_map["transformation"]["weight_pct"] == 25
    assert factor_map["topology"]["weight_pct"] == 25
    assert factor_map["expression"]["weight_pct"] == 15
    assert factor_map["runtime"]["weight_pct"] == 15

    # Criticality model validation
    criticality = data["criticality"]
    assert criticality["model_name"] == "Criticality Evaluation Model"
    assert criticality["total_weight_pct"] == 100
    assert criticality["technical_weight_pct"] == 60
    assert criticality["operational_weight_pct"] == 40
    assert len(criticality["factors"]) == 5

    criticality_weight_sum = sum(f["weight_pct"] for f in criticality["factors"])
    assert criticality_weight_sum == 100

    crit_factor_map = {f["id"]: f for f in criticality["factors"]}
    assert crit_factor_map["downstream_outputs"]["weight_pct"] == 20
    assert crit_factor_map["downstream_outputs"]["category"] == "Technical"
    assert crit_factor_map["upstream_sources"]["weight_pct"] == 20
    assert crit_factor_map["upstream_sources"]["category"] == "Technical"
    assert crit_factor_map["etl_consumers"]["weight_pct"] == 20
    assert crit_factor_map["etl_consumers"]["category"] == "Technical"
    assert crit_factor_map["last_run"]["weight_pct"] == 20
    assert crit_factor_map["last_run"]["category"] == "Operational"
    assert crit_factor_map["frequency"]["weight_pct"] == 20
    assert crit_factor_map["frequency"]["category"] == "Operational"


def test_complexity_model_weights_synchronization():
    """Verify Complexity factor metadata matches calculation weights 1:1."""
    model = get_complexity_evaluation_model()
    factors = model["factors"]
    assert len(factors) == len(COMPLEXITY_WEIGHTS)
    for f in factors:
        expected_pct = int(COMPLEXITY_WEIGHTS[f["id"]] * 100)
        assert f["weight_pct"] == expected_pct
    assert sum(f["weight_pct"] for f in factors) == 100


def test_criticality_model_weights_synchronization():
    """Verify Criticality factor metadata matches calculation weights 1:1."""
    model = get_criticality_evaluation_model()
    factors = model["factors"]
    assert len(factors) == 5
    for f in factors:
        assert f["weight_pct"] == int(CRITICALITY_FACTOR_WEIGHT * 100)
    assert sum(f["weight_pct"] for f in factors) == 100
    assert model["technical_weight_pct"] == int(TECHNICAL_WEIGHT_TOTAL * 100)
    assert model["operational_weight_pct"] == int(OPERATIONAL_WEIGHT_TOTAL * 100)
