"""Tests for RCA API endpoints."""

import uuid

import pytest


def _create_investigation(client):
    response = client.post(
        "/api/v1/investigations",
        json={"title": "RCA API test"},
    )
    assert response.status_code == 201
    return response.json()


def _add_text_evidence(client, investigation_id):
    response = client.post(
        f"/api/v1/investigations/{investigation_id}/ingest-text",
        json={
            "title": "batch-report.txt",
            "content": "Temperature exceeded 82 C during synthesis step.",
        },
    )
    assert response.status_code == 201
    return response.json()


class TestRCAEndpoints:
    def test_list_rca_runs_empty(self, client):
        inv = _create_investigation(client)
        response = client.get(
            f"/api/v1/investigations/{inv['id']}/rca"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_rca_run_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/investigations/{inv['id']}/rca/{fake_id}"
        )
        assert response.status_code == 404

    def test_start_rca_no_evidence(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/rca"
        )
        assert response.status_code == 422

    def test_start_rca_investigation_not_found(
        self, client
    ):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/investigations/{fake_id}/rca"
        )
        assert response.status_code == 404


class TestReviewEndpoints:
    def test_review_evidence_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/evidence/{fake_id}",
            json={"review_status": "accepted"},
        )
        assert response.status_code == 404

    def test_review_evidence_accept(self, client):
        inv = _create_investigation(client)
        _add_text_evidence(client, inv["id"])

        # Get the evidence item
        ev_response = client.get(
            f"/api/v1/investigations/{inv['id']}/evidence"
        )
        assert ev_response.status_code == 200
        items = ev_response.json()["items"]
        assert len(items) > 0
        evidence_id = items[0]["id"]

        # Accept it
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/evidence/{evidence_id}",
            json={"review_status": "accepted"},
        )
        assert response.status_code == 200
        assert response.json()["review_status"] == "accepted"

    def test_review_evidence_reject(self, client):
        inv = _create_investigation(client)
        _add_text_evidence(client, inv["id"])

        ev_response = client.get(
            f"/api/v1/investigations/{inv['id']}/evidence"
        )
        evidence_id = ev_response.json()["items"][0]["id"]

        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/evidence/{evidence_id}",
            json={
                "review_status": "rejected",
                "review_note": "Not relevant",
            },
        )
        assert response.status_code == 200
        assert response.json()["review_status"] == "rejected"

    def test_review_hypothesis_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/hypotheses/{fake_id}",
            json={"status": "under_review"},
        )
        assert response.status_code == 404

    def test_why_step_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/why-steps/{fake_id}",
            json={"question": "Updated question"},
        )
        assert response.status_code == 404

    def test_evidence_gap_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/evidence-gaps/{fake_id}",
            json={"status": "addressed"},
        )
        assert response.status_code == 404


class TestIngestionEndpoints:
    def test_ingest_text(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/ingest-text",
            json={
                "title": "Lab Report",
                "content": "Temperature was 82 degrees.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["evidence_items_created"] == 1
        assert data["document"]["document_type"] == "text"

    def test_ingest_text_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/investigations/{fake_id}/ingest-text",
            json={
                "title": "Report",
                "content": "Some content",
            },
        )
        assert response.status_code == 404

    def test_ingest_email(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/ingest-email",
            json={
                "subject": "Batch deviation report",
                "sender": "qa@pharma.com",
                "date": "2024-01-15",
                "body": "Temperature deviation observed.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["evidence_items_created"] == 1
        assert data["document"]["document_type"] == "email"

    def test_ingest_email_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/investigations/{fake_id}/ingest-email",
            json={
                "subject": "Report",
                "sender": "user@test.com",
                "body": "Content",
            },
        )
        assert response.status_code == 404

    def test_ingest_text_empty_title(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/ingest-text",
            json={"title": "", "content": "Some content"},
        )
        assert response.status_code == 422

    def test_ingest_email_empty_body(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/ingest-email",
            json={
                "subject": "Test",
                "sender": "user@test.com",
                "body": "",
            },
        )
        assert response.status_code == 422

    def test_text_evidence_accessible(self, client):
        """Text-ingested evidence appears in the evidence list."""
        inv = _create_investigation(client)
        client.post(
            f"/api/v1/investigations/{inv['id']}/ingest-text",
            json={
                "title": "Report",
                "content": "Temperature was 82 degrees.",
            },
        )
        response = client.get(
            f"/api/v1/investigations/{inv['id']}/evidence"
        )
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert "82 degrees" in items[0]["content"]


class TestCAPAEndpoints:
    def test_list_capa_empty(self, client):
        inv = _create_investigation(client)
        response = client.get(
            f"/api/v1/investigations/{inv['id']}/capa"
        )
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    def test_capa_not_found(self, client):
        inv = _create_investigation(client)
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/investigations/{inv['id']}"
            f"/capa/{fake_id}",
            json={"status": "approved"},
        )
        assert response.status_code == 404

    def test_generate_capa_no_rca(self, client):
        inv = _create_investigation(client)
        response = client.post(
            f"/api/v1/investigations/{inv['id']}/capa"
        )
        assert response.status_code == 422


class TestCopilotEndpoints:
    def test_copilot_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/investigations/{fake_id}/copilot",
            json={"message": "What happened?"},
        )
        assert response.status_code == 404
