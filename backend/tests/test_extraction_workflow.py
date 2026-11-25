import importlib

import pymupdf

from app.agents.nodes.detect_conflicts import detect_conflicts
from app.agents.nodes.extract_facts import build_chunks
from app.agents.nodes.validate_facts import validate_facts
from app.api.routes import documents as documents_route
from app.core.config import Settings

extract_node = importlib.import_module(
    "app.agents.nodes.extract_facts"
)


def make_pdf(text: str | None) -> bytes:
    """Generate a synthetic PDF."""
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def create_investigation(client):
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "Synthetic API investigation",
            "product_name": "Metformin API",
            "batch_number": "MTF26001",
        },
    )
    assert response.status_code == 201
    return response.json()


def upload_source_pdf(
    client,
    investigation_id,
    content,
    tmp_path,
    monkeypatch,
):
    """Upload a synthetic document into isolated storage."""
    settings = Settings(
        storage_dir=tmp_path,
        max_upload_size_mb=1,
        max_pdf_pages=10,
        max_extracted_text_chars=100000,
    )
    monkeypatch.setattr(
        documents_route,
        "get_settings",
        lambda: settings,
    )
    response = client.post(
        (
            f"/api/v1/investigations/"
            f"{investigation_id}/documents"
        ),
        files={
            "file": (
                "synthetic_report.pdf",
                content,
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201
    return response.json()


def mock_extraction(monkeypatch, facts):
    """Replace Groq inference with a deterministic response."""

    def fake_generate(**kwargs):
        assert kwargs["schema_name"] == "incident_extraction"
        return {
            "summary": (
                "Synthetic incident information extracted."
            ),
            "facts": facts,
            "warnings": [],
        }

    monkeypatch.setattr(
        extract_node,
        "generate_structured_response",
        fake_generate,
    )


def test_chunking_preserves_source_offsets():
    pages = [
        {
            "source_document_id": "document-001",
            "original_filename": "report.pdf",
            "page_number": 1,
            "text": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "source_start_char": 0,
        }
    ]
    chunks = build_chunks(
        pages,
        chunk_chars=10,
        overlap_chars=2,
    )
    assert len(chunks) == 3
    assert chunks[0]["chunk_start_char"] == 0
    assert chunks[1]["chunk_start_char"] == 8
    assert chunks[2]["chunk_start_char"] == 16
    assert chunks[0]["chunk_text"] == "ABCDEFGHIJ"
    assert chunks[1]["chunk_text"] == "IJKLMNOPQR"
    assert chunks[2]["chunk_text"] == "QRSTUVWXYZ"


def test_exact_source_quotation_is_accepted():
    page = {
        "source_document_id": "document-001",
        "original_filename": "report.pdf",
        "page_number": 1,
        "text": "Batch Number: MTF26001",
        "source_start_char": 0,
    }
    chunk = {
        "chunk_id": 0,
        "source_document_id": "document-001",
        "original_filename": "report.pdf",
        "page_number": 1,
        "chunk_start_char": 0,
        "chunk_text": page["text"],
    }
    state = {
        "investigation_id": "investigation-001",
        "source_pages": [page],
        "chunks": [chunk],
        "raw_facts": [
            {
                "field_name": "batch_number",
                "extracted_value": "MTF26001",
                "source_quote": "Batch Number: MTF26001",
                "page_number": 1,
                "chunk_id": 0,
                "source_document_id": "document-001",
                "original_filename": "report.pdf",
            }
        ],
    }
    result = validate_facts(state)
    assert len(result["validated_facts"]) == 1
    assert result["rejected_facts"] == []
    fact = result["validated_facts"][0]
    assert fact["extracted_value"] == "MTF26001"
    assert fact["source_start_char"] == 0
    assert fact["source_end_char"] == len(
        "Batch Number: MTF26001"
    )


def test_invented_source_quotation_is_rejected():
    state = {
        "investigation_id": "investigation-001",
        "source_pages": [
            {
                "source_document_id": "document-001",
                "original_filename": "report.pdf",
                "page_number": 1,
                "text": "Batch Number: MTF26001",
                "source_start_char": 0,
            }
        ],
        "chunks": [
            {
                "chunk_id": 0,
                "source_document_id": "document-001",
                "original_filename": "report.pdf",
                "page_number": 1,
                "chunk_start_char": 0,
                "chunk_text": "Batch Number: MTF26001",
            }
        ],
        "raw_facts": [
            {
                "field_name": "batch_number",
                "extracted_value": "MTF99999",
                "source_quote": "Batch Number: MTF99999",
                "page_number": 1,
                "chunk_id": 0,
                "source_document_id": "document-001",
                "original_filename": "report.pdf",
            }
        ],
    }
    result = validate_facts(state)
    assert result["validated_facts"] == []
    assert len(result["rejected_facts"]) == 1
    assert (
        result["rejected_facts"][0]["reason"]
        == "quotation_not_found_in_source_chunk"
    )


def test_conflicting_batch_values_are_detected():
    facts = [
        {
            "field_name": "batch_number",
            "extracted_value": "MTF26001",
            "content": "Batch Number: MTF26001",
            "source_document_id": "document-001",
            "original_filename": "deviation.pdf",
            "page_number": 1,
        },
        {
            "field_name": "batch_number",
            "extracted_value": "MTF26010",
            "content": "Batch Number: MTF26010",
            "source_document_id": "document-002",
            "original_filename": "lab_report.pdf",
            "page_number": 2,
        },
    ]
    result = detect_conflicts(
        {
            "investigation_id": "investigation-001",
            "validated_facts": facts,
        }
    )
    assert len(result["field_conflicts"]) == 1
    conflict = result["field_conflicts"][0]
    assert conflict["field_name"] == "batch_number"
    assert len(conflict["candidates"]) == 2
    assert (
        conflict["status"] == "requires_human_resolution"
    )


def test_langgraph_extracts_and_persists_fact(
    client,
    tmp_path,
    monkeypatch,
):
    investigation = create_investigation(client)
    upload_source_pdf(
        client,
        investigation["id"],
        make_pdf("Batch Number: MTF26001"),
        tmp_path,
        monkeypatch,
    )
    mock_extraction(
        monkeypatch,
        [
            {
                "field_name": "batch_number",
                "extracted_value": "MTF26001",
                "source_quote": "Batch Number: MTF26001",
                "page_number": 1,
            }
        ],
    )
    response = client.post(
        (
            f"/api/v1/investigations/"
            f"{investigation['id']}/extract-facts"
        )
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["validated_fact_count"] == 1
    assert result["new_facts_count"] == 1
    assert result["duplicate_facts_count"] == 0
    assert len(result["extracted_facts"]) == 1
    fact = result["extracted_facts"][0]
    assert fact["field_name"] == "batch_number"
    assert fact["extracted_value"] == "MTF26001"
    assert fact["review_status"] == "pending"

    # Verify that the claim was actually stored in the database.
    evidence_response = client.get(
        (
            f"/api/v1/investigations/"
            f"{investigation['id']}/evidence"
        )
    )
    assert evidence_response.status_code == 200
    evidence_items = evidence_response.json()["items"]
    extracted_items = [
        item
        for item in evidence_items
        if item["evidence_kind"] == "extracted_fact"
    ]
    assert len(extracted_items) == 1
    assert extracted_items[0]["extracted_value"] == "MTF26001"


def test_repeated_extraction_does_not_create_duplicates(
    client,
    tmp_path,
    monkeypatch,
):
    investigation = create_investigation(client)
    upload_source_pdf(
        client,
        investigation["id"],
        make_pdf("Batch Number: MTF26001"),
        tmp_path,
        monkeypatch,
    )
    mock_extraction(
        monkeypatch,
        [
            {
                "field_name": "batch_number",
                "extracted_value": "MTF26001",
                "source_quote": "Batch Number: MTF26001",
                "page_number": 1,
            }
        ],
    )
    endpoint = (
        f"/api/v1/investigations/"
        f"{investigation['id']}/extract-facts"
    )
    first = client.post(endpoint)
    second = client.post(endpoint)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["new_facts_count"] == 1
    assert second.json()["new_facts_count"] == 0
    assert second.json()["duplicate_facts_count"] == 1
    assert len(second.json()["extracted_facts"]) == 1


def test_investigation_without_documents_returns_422(
    client,
):
    investigation = create_investigation(client)
    response = client.post(
        (
            f"/api/v1/investigations/"
            f"{investigation['id']}/extract-facts"
        )
    )
    assert response.status_code == 422


def test_document_without_extractable_text_returns_warning(
    client,
    tmp_path,
    monkeypatch,
):
    investigation = create_investigation(client)
    upload_source_pdf(
        client,
        investigation["id"],
        make_pdf(None),
        tmp_path,
        monkeypatch,
    )
    response = client.post(
        (
            f"/api/v1/investigations/"
            f"{investigation['id']}/extract-facts"
        )
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "no_extractable_text"
    assert result["new_facts_count"] == 0
    assert result["extracted_facts"] == []
    assert any(
        "OCR is required" in warning
        for warning in result["warnings"]
    )


def test_incident_date_extraction_normalizes_to_iso_format(
    client,
    tmp_path,
    monkeypatch,
):
    investigation = create_investigation(client)
    upload_source_pdf(
        client,
        investigation["id"],
        make_pdf("Incident Date: 20 November 2026"),
        tmp_path,
        monkeypatch,
    )
    mock_extraction(
        monkeypatch,
        [
            {
                "field_name": "incident_date",
                "extracted_value": "20 November 2026",
                "source_quote": "Incident Date: 20 November 2026",
                "page_number": 1,
            }
        ],
    )
    response = client.post(
        f"/api/v1/investigations/{investigation['id']}/extract-facts"
    )
    assert response.status_code == 200
    facts = response.json()["extracted_facts"]
    assert len(facts) == 1
    assert facts[0]["field_name"] == "incident_date"
    assert facts[0]["extracted_value"] == "2026-11-20"

    # Applying accepted fact updates Investigation.incident_date cleanly
    apply_resp = client.patch(
        f"/api/v1/investigations/{investigation['id']}/evidence/{facts[0]['id']}",
        json={"review_status": "accepted", "apply_to_investigation": True},
    )
    assert apply_resp.status_code == 200

    inv_resp = client.get(f"/api/v1/investigations/{investigation['id']}")
    assert inv_resp.status_code == 200
    assert inv_resp.json()["incident_date"] == "2026-11-20"
