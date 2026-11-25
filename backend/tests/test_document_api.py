from uuid import uuid4

import pymupdf
import pytest

from app.api.routes import documents as documents_route
from app.core.config import Settings


def make_pdf(page_texts: list[str | None]) -> bytes:
    """Generate a PDF with the supplied page contents."""
    document = pymupdf.open()
    for page_text in page_texts:
        page = document.new_page()
        if page_text:
            page.insert_text(
                (72, 72),
                page_text,
            )
    content = document.tobytes()
    document.close()
    return content


def create_investigation(client):
    """Create a parent investigation."""
    response = client.post(
        "/api/v1/investigations",
        json={
            "title": "Document ingestion test investigation",
            "product_name": "Metformin API",
            "batch_number": "MTF26001",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def document_settings(tmp_path, monkeypatch):
    """
    Give each document test isolated file storage.
    No production or development upload directory is touched.
    """
    settings = Settings(
        storage_dir=tmp_path,
        max_upload_size_mb=1,
        max_pdf_pages=10,
        max_extracted_text_chars=100_000,
    )
    monkeypatch.setattr(
        documents_route,
        "get_settings",
        lambda: settings,
    )
    return settings


def test_upload_pdf_creates_document_and_evidence(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    pdf_content = make_pdf(
        [
            "Deviation report. Batch MTF26001.",
            "Foreign matter detected in API drum.",
        ]
    )
    response = client.post(
        (
            f"/api/v1/investigations/"
            f"{investigation['id']}/documents"
        ),
        files={
            "file": (
                "deviation_report.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201
    result = response.json()
    document = result["document"]
    assert document["investigation_id"] == investigation["id"]
    assert document["original_filename"] == (
        "deviation_report.pdf"
    )
    assert document["page_count"] == 2
    assert document["extraction_status"] == "text_extracted"
    assert result["evidence_items_created"] == 2
    assert result["pages_without_text"] == []
    assert result["extracted_text_characters"] > 0
    # Internal storage paths must never be exposed.
    assert "storage_key" not in document


def test_document_metadata_and_download(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    pdf_content = make_pdf(
        ["ProofChain original document content."]
    )
    upload_response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "source.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 201
    document = upload_response.json()["document"]
    document_id = document["id"]
    investigation_id = investigation["id"]

    metadata_response = client.get(
        (
            f"/api/v1/investigations/{investigation_id}"
            f"/documents/{document_id}"
        )
    )
    assert metadata_response.status_code == 200
    assert metadata_response.json()["id"] == document_id

    download_response = client.get(
        (
            f"/api/v1/investigations/{investigation_id}"
            f"/documents/{document_id}/download"
        )
    )
    assert download_response.status_code == 200
    assert download_response.content == pdf_content


def test_list_documents(client, document_settings):
    investigation = create_investigation(client)
    pdf_content = make_pdf(["Document one."])
    client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "first.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    response = client.get(
        f"/api/v1/investigations/{investigation['id']}/documents"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["original_filename"] == "first.pdf"


def test_list_evidence_and_retrieve_item(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    pdf_content = make_pdf(
        [
            "Manufacturing deviation observed.",
            "Batch MTF26001 requires investigation.",
        ]
    )
    client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "report.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    evidence_response = client.get(
        f"/api/v1/investigations/{investigation['id']}/evidence"
    )
    assert evidence_response.status_code == 200
    evidence_data = evidence_response.json()
    assert evidence_data["total"] == 2
    first_evidence = evidence_data["items"][0]
    assert first_evidence["evidence_kind"] == "source_excerpt"
    assert first_evidence["review_status"] == "pending"
    assert first_evidence["page_number"] == 1
    assert first_evidence["source_start_char"] == 0
    assert first_evidence["source_end_char"] > 0

    evidence_id = first_evidence["id"]
    detail_response = client.get(
        (
            f"/api/v1/investigations/{investigation['id']}"
            f"/evidence/{evidence_id}"
        )
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == evidence_id


def test_evidence_can_be_filtered_by_document(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    first = make_pdf(["First document page."])
    second = make_pdf(
        [
            "Second document page one.",
            "Second document page two.",
        ]
    )
    first_response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": ("first.pdf", first, "application/pdf")
        },
    )
    second_response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": ("second.pdf", second, "application/pdf")
        },
    )
    first_document_id = (
        first_response.json()["document"]["id"]
    )
    second_document_id = (
        second_response.json()["document"]["id"]
    )

    response = client.get(
        (
            f"/api/v1/investigations/{investigation['id']}"
            f"/evidence?document_id={first_document_id}"
        )
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert (
        data["items"][0]["source_document_id"]
        == first_document_id
    )
    assert second_document_id != first_document_id


def test_partial_text_document_creates_only_text_evidence(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    pdf_content = make_pdf(
        [
            "This page has extractable text.",
            None,
        ]
    )
    response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "partial.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["document"]["page_count"] == 2
    assert data["document"]["extraction_status"] == "partial_text"
    assert data["evidence_items_created"] == 1
    assert data["pages_without_text"] == [2]


def test_upload_for_missing_investigation_returns_404(
    client,
):
    missing_id = uuid4()
    response = client.post(
        f"/api/v1/investigations/{missing_id}/documents",
        files={
            "file": (
                "report.pdf",
                make_pdf(["Test document."]),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 404


def test_invalid_pdf_upload_returns_415(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "invalid.pdf",
                b"This is not a PDF.",
                "application/pdf",
            )
        },
    )
    assert response.status_code == 415


def test_wrong_extension_returns_415(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "report.txt",
                make_pdf(["PDF content."]),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 415


def test_upload_size_limit_returns_413(
    client,
    document_settings,
):
    investigation = create_investigation(client)
    oversized_content = (
        b"%PDF-" + b"A" * (1024 * 1024)
    )
    response = client.post(
        f"/api/v1/investigations/{investigation['id']}/documents",
        files={
            "file": (
                "large.pdf",
                oversized_content,
                "application/pdf",
            )
        },
    )
    assert response.status_code == 413


def test_document_cannot_be_retrieved_under_another_investigation(
    client,
    document_settings,
):
    first_investigation = create_investigation(client)
    second_investigation = create_investigation(client)
    upload_response = client.post(
        (
            f"/api/v1/investigations/"
            f"{first_investigation['id']}/documents"
        ),
        files={
            "file": (
                "private.pdf",
                make_pdf(["Private evidence."]),
                "application/pdf",
            )
        },
    )
    document_id = upload_response.json()["document"]["id"]
    response = client.get(
        (
            f"/api/v1/investigations/"
            f"{second_investigation['id']}"
            f"/documents/{document_id}"
        )
    )
    assert response.status_code == 404


def test_missing_investigation_evidence_returns_404(
    client,
):
    response = client.get(
        f"/api/v1/investigations/{uuid4()}/evidence"
    )
    assert response.status_code == 404
