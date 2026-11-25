import hashlib
from io import BytesIO
from uuid import uuid4

import pymupdf
import pytest
from fastapi import UploadFile

from app.services.document_storage import (
    DocumentStorageError,
    InvalidDocumentUpload,
    UploadSizeLimitExceeded,
    delete_stored_file,
    resolve_storage_path,
    store_pdf,
)


def make_pdf() -> bytes:
    """Generate a valid one-page PDF for testing."""

    document = pymupdf.open()

    page = document.new_page()

    page.insert_text(
        (72, 72),
        "ProofChain document storage test.",
    )

    content = document.tobytes()

    document.close()

    return content


def make_upload(
    filename: str,
    content: bytes,
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
    )


def test_store_valid_pdf(tmp_path):

    content = make_pdf()

    upload = make_upload(
        "deviation_report.pdf",
        content,
    )

    investigation_id = uuid4()
    document_id = uuid4()

    result = store_pdf(
        upload,
        storage_dir=tmp_path,
        investigation_id=investigation_id,
        document_id=document_id,
        max_size_bytes=1024 * 1024,
    )

    assert result.absolute_path.exists()

    assert result.original_filename == "deviation_report.pdf"

    assert result.file_size_bytes == len(content)

    assert result.sha256 == hashlib.sha256(
        content
    ).hexdigest()

    assert result.content_type == "application/pdf"

    assert result.storage_key == (
        f"{investigation_id}/{document_id}.pdf"
    )


def test_filename_path_components_are_removed(tmp_path):

    upload = make_upload(
        "../../private/report.pdf",
        make_pdf(),
    )

    result = store_pdf(
        upload,
        storage_dir=tmp_path,
        investigation_id=uuid4(),
        document_id=uuid4(),
        max_size_bytes=1024 * 1024,
    )

    assert result.original_filename == "report.pdf"

    assert result.absolute_path.exists()


def test_non_pdf_extension_is_rejected(tmp_path):

    upload = make_upload(
        "report.txt",
        make_pdf(),
    )

    with pytest.raises(InvalidDocumentUpload):

        store_pdf(
            upload,
            storage_dir=tmp_path,
            investigation_id=uuid4(),
            document_id=uuid4(),
            max_size_bytes=1024 * 1024,
        )


def test_invalid_pdf_signature_is_rejected(tmp_path):

    upload = make_upload(
        "fake.pdf",
        b"This is not a PDF document.",
    )

    with pytest.raises(InvalidDocumentUpload):

        store_pdf(
            upload,
            storage_dir=tmp_path,
            investigation_id=uuid4(),
            document_id=uuid4(),
            max_size_bytes=1024 * 1024,
        )


def test_empty_file_is_rejected(tmp_path):

    upload = make_upload(
        "empty.pdf",
        b"",
    )

    with pytest.raises(InvalidDocumentUpload):

        store_pdf(
            upload,
            storage_dir=tmp_path,
            investigation_id=uuid4(),
            document_id=uuid4(),
            max_size_bytes=1024 * 1024,
        )


def test_upload_size_limit_is_enforced(tmp_path):

    upload = make_upload(
        "large.pdf",
        b"%PDF-" + (b"A" * 2048),
    )

    with pytest.raises(UploadSizeLimitExceeded):

        store_pdf(
            upload,
            storage_dir=tmp_path,
            investigation_id=uuid4(),
            document_id=uuid4(),
            max_size_bytes=1024,
        )


def test_storage_path_rejects_directory_traversal(tmp_path):

    with pytest.raises(DocumentStorageError):

        resolve_storage_path(
            tmp_path,
            "../outside.pdf",
        )


def test_delete_stored_file(tmp_path):

    upload = make_upload(
        "report.pdf",
        make_pdf(),
    )

    result = store_pdf(
        upload,
        storage_dir=tmp_path,
        investigation_id=uuid4(),
        document_id=uuid4(),
        max_size_bytes=1024 * 1024,
    )

    assert result.absolute_path.exists()

    delete_stored_file(
        tmp_path,
        result.storage_key,
    )

    assert not result.absolute_path.exists()
