"""Tests for in-app rationalisation recommendation email composition and dispatch."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.schemas import (
    ConsolidationDecisionDTO,
    DataSubsumptionEvidenceDTO,
    DeterministicMetricsDTO,
    PortfolioOverviewDTO,
    PortfolioWorkflowSummaryDTO,
    RationalisationCandidateDTO,
)
from backend.app.services.email_service import (
    EmailDeliveryError,
    EmailService,
    EmailValidationError,
    SMTPEmailTransport,
    get_email_service,
    set_default_email_service,
    set_default_transport,
)
from backend.app.services.storage import get_storage


class MockEmailTransport:
    """Mock email transport for recording dispatches during tests."""

    def __init__(self, should_fail: bool = False, fail_message: str = "Mock SMTP transport error"):
        self.sent_messages: list[dict] = []
        self.should_fail = should_fail
        self.fail_message = fail_message

    def send_email(
        self,
        from_addr: str,
        to_addrs: list[str],
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        if self.should_fail:
            raise EmailDeliveryError(self.fail_message)
        self.sent_messages.append({
            "from_addr": from_addr,
            "to_addrs": to_addrs,
            "subject": subject,
            "text_body": text_body,
            "html_body": html_body,
        })


class MockPortfolioAnalysis:
    """Mock portfolio analysis container matching portfolio storage protocol."""

    def __init__(
        self,
        portfolio_id: str = "test-port-1",
        portfolio_name: str = "Test Portfolio",
        rationalisation_candidates: list | None = None,
    ):
        self.portfolio_id = portfolio_id
        self.portfolio_name = portfolio_name
        self.workflows = []
        self.metrics = {}
        self.shared_sources = []
        self.shared_targets = []
        self.relationships = []
        self.rationalisation_candidates = rationalisation_candidates or []
        self.business_areas = []
        self.created_at = 1700000000.0

    def to_dict(self):
        return {
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "workflow_count": len(self.workflows),
            "workflows": self.workflows,
            "metrics": {
                "total_workflows": len(self.workflows),
                "successful_workflows": len(self.workflows),
                "failed_workflows": 0,
                "total_tools": 10,
                "total_sources": 2,
                "unique_sources": 2,
                "total_targets": 2,
                "unique_targets": 2,
                "shared_sources_count": 0,
                "shared_targets_count": 0,
                "inspection_sinks_count": 0,
                "tool_distribution": {},
            },
            "shared_sources": self.shared_sources,
            "shared_targets": self.shared_targets,
            "relationships": self.relationships,
            "rationalisation_candidates": [
                c.model_dump() if hasattr(c, "model_dump") else c
                for c in self.rationalisation_candidates
            ],
            "business_area_counts": {},
            "business_area_descriptions": {},
            "business_areas": self.business_areas,
            "created_at": self.created_at,
        }


@pytest.fixture(autouse=True)
def setup_mock_storage_and_email(monkeypatch):
    """Fixture to ensure clean mock transport and test portfolio in storage."""
    mock_transport = MockEmailTransport()
    set_default_transport(mock_transport)

    storage = get_storage()
    # Populate a test portfolio with CONSOLIDATE, RETIRE, and KEEP candidates
    cand_consolidate = RationalisationCandidateDTO(
        candidate_id="cand_merge_1",
        workflow_ids=["wf_legacy_a", "wf_target_b"],
        workflow_names=["Legacy_A.yxmd", "Target_B.yxmd"],
        recommendation_type="CONSOLIDATE",
        confidence="HIGH",
        opportunity_score=88.5,
        reasoning="Legacy_A data processing is completely subsumed by Target_B.",
        validation_requirements=[
            "Verify all legacy downstream consumers have switched to Target_B.",
            "Compare record counts on target datasets.",
        ],
        deterministic_metrics=DeterministicMetricsDTO(
            source_overlap=1.0,
            target_overlap=1.0,
            transformation_similarity=0.92,
            schema_similarity=0.95,
            grain_similarity=1.0,
            dag_similarity=0.88,
            frequency_overlap=1.0,
        ),
    )

    cand_retire = RationalisationCandidateDTO(
        candidate_id="cand_retire_1",
        workflow_ids=["wf_obsolete_c"],
        workflow_names=["Obsolete_C.yxmd"],
        recommendation_type="RETIRE",
        confidence="HIGH",
        opportunity_score=95.0,
        reasoning="Target dataset has been decommissioned and no active consumers remain.",
        validation_requirements=[
            "Confirm scheduled job is disabled in Scheduler.",
        ],
    )

    cand_keep = RationalisationCandidateDTO(
        candidate_id="cand_keep_1",
        workflow_ids=["wf_critical_d"],
        workflow_names=["Critical_D.yxmd"],
        recommendation_type="KEEP",
        confidence="HIGH",
        opportunity_score=10.0,
        reasoning="Distinct business logic with no overlap.",
    )

    port = MockPortfolioAnalysis(
        portfolio_id="test_port_email",
        portfolio_name="Email Test Portfolio",
        rationalisation_candidates=[cand_consolidate, cand_retire, cand_keep],
    )
    storage.save_portfolio(port)

    yield mock_transport

    set_default_email_service(None)


def test_send_email_success_with_mock_transport(setup_mock_storage_and_email):
    """Test successful in-app email dispatch for a CONSOLIDATE recommendation."""
    mock_transport = setup_mock_storage_and_email
    client = TestClient(app)

    payload = {
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_merge_1",
        "to_email": "stakeholder@enterprise.corp",
        "subject": "ETL Rationalisation Recommendation – Consolidation: Legacy_A.yxmd → Target_B.yxmd",
        "body": "Consolidation details for Legacy_A into Target_B.",
        "from_email": "notifications@awa-etl.internal",
    }

    response = client.post("/api/portfolio/rationalisation/email", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["recipient"] == "stakeholder@enterprise.corp"
    assert "sent successfully" in data["message"].lower()

    # Verify transport recorded the message correctly
    assert len(mock_transport.sent_messages) == 1
    sent = mock_transport.sent_messages[0]
    assert sent["from_addr"] == "notifications@awa-etl.internal"
    assert sent["to_addrs"] == ["stakeholder@enterprise.corp"]
    assert sent["subject"] == payload["subject"]
    assert sent["text_body"] == payload["body"]
    assert "<div" in sent["html_body"]


def test_send_email_retire_recommendation(setup_mock_storage_and_email):
    """Test successful in-app email dispatch for a RETIRE recommendation."""
    mock_transport = setup_mock_storage_and_email
    client = TestClient(app)

    payload = {
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_retire_1",
        "to_email": "owner@company.com",
        "subject": "ETL Rationalisation Recommendation – Retirement: Obsolete_C.yxmd",
        "body": "Recommendation to retire Obsolete_C.yxmd as all downstream consumers migrated.",
    }

    response = client.post("/api/portfolio/rationalisation/email", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["recipient"] == "owner@company.com"


def test_send_email_keep_recommendation_rejected():
    """Verify that non-actionable (KEEP) recommendations are rejected for email dispatch."""
    client = TestClient(app)

    payload = {
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_keep_1",
        "to_email": "architect@company.com",
        "subject": "ETL Rationalisation Recommendation",
        "body": "Test body",
    }

    response = client.post("/api/portfolio/rationalisation/email", json=payload)
    assert response.status_code == 400
    assert "CONSOLIDATE and RETIRE" in response.text


def test_send_email_invalid_recipient_rejected():
    """Verify rejection of malformed or invalid recipient email addresses."""
    client = TestClient(app)

    invalid_emails = [
        "not-an-email",
        "user@",
        "@example.com",
        "user@example",
        "user @example.com",
        "",
    ]

    for inv_email in invalid_emails:
        payload = {
            "portfolio_id": "test_port_email",
            "candidate_id": "cand_merge_1",
            "to_email": inv_email,
            "subject": "Test Subject",
            "body": "Test Body",
        }
        response = client.post("/api/portfolio/rationalisation/email", json=payload)
        assert response.status_code in (400, 422), f"Expected validation failure for '{inv_email}'"


def test_send_email_empty_subject_or_body_rejected():
    """Verify rejection of empty or whitespace-only subject and body."""
    client = TestClient(app)

    # Empty subject
    res1 = client.post("/api/portfolio/rationalisation/email", json={
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_merge_1",
        "to_email": "valid@example.com",
        "subject": "   ",
        "body": "Some body content",
    })
    assert res1.status_code == 422

    # Empty body
    res2 = client.post("/api/portfolio/rationalisation/email", json={
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_merge_1",
        "to_email": "valid@example.com",
        "subject": "Valid Subject",
        "body": " \n \t ",
    })
    assert res2.status_code == 422


def test_send_email_portfolio_not_found():
    """Verify 404 response when portfolio ID does not exist."""
    client = TestClient(app)

    payload = {
        "portfolio_id": "non_existent_portfolio_id_9999",
        "candidate_id": "cand_merge_1",
        "to_email": "valid@example.com",
        "subject": "Valid Subject",
        "body": "Valid body",
    }
    response = client.post("/api/portfolio/rationalisation/email", json=payload)
    assert response.status_code == 404
    assert "not found" in response.text.lower()


def test_send_email_transport_failure_handled_safely():
    """Verify transport errors are safely captured and returned with 500 without leaking credentials."""
    failing_transport = MockEmailTransport(should_fail=True, fail_message="Authentication failed for user secret_user")
    set_default_transport(failing_transport)

    client = TestClient(app)
    payload = {
        "portfolio_id": "test_port_email",
        "candidate_id": "cand_merge_1",
        "to_email": "user@example.com",
        "subject": "Subject",
        "body": "Body",
    }
    response = client.post("/api/portfolio/rationalisation/email", json=payload)
    assert response.status_code == 500
    detail = response.json().get("detail", {})
    assert detail.get("code") == "EMAIL_DELIVERY_FAILED"


def test_email_service_html_escaping():
    """Test EmailService safely escapes HTML and handles special characters."""
    mock_transport = MockEmailTransport()
    service = EmailService(transport=mock_transport)

    xss_payload = "<script>alert('xss');</script> & <b>bold</b> \"quotes\" 'single'"
    res = service.send_email(
        to_email="test@example.com",
        subject="XSS Test",
        body=xss_payload,
    )
    assert res["status"] == "success"
    assert len(mock_transport.sent_messages) == 1
    sent = mock_transport.sent_messages[0]
    html_content = sent["html_body"]
    assert "<script>" not in html_content
    assert "&lt;script&gt;alert(&#x27;xss&#x27;);&lt;/script&gt;" in html_content
    assert "&amp;" in html_content
    assert "&quot;quotes&quot;" in html_content


def test_smtp_transport_missing_host():
    """Test SMTPEmailTransport raises EmailDeliveryError when host is not set."""
    transport = SMTPEmailTransport(host=None)
    with pytest.raises(EmailDeliveryError, match="SMTP host is not configured"):
        transport.send_email(
            from_addr="from@test.com",
            to_addrs=["to@test.com"],
            subject="Subj",
            text_body="Body",
        )
