import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.models.source_document import SourceDocument
from app.services.document_extraction import (
    extract_pdf,
)
from app.services.document_storage import (
    StoredPDF,
    delete_stored_file,
    store_pdf,
)
from app.services.exceptions import InvestigationNotFoundError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentIngestionResult:
    """Result of successfully ingesting a PDF."""

    document: SourceDocument
    evidence_items_created: int
    pages_without_text: list[int]
    extracted_text_characters: int


def ingest_pdf(
    db: Session,
    investigation_id: UUID,
    upload: UploadFile,
    settings: Settings,
) -> DocumentIngestionResult:
    """
    Validate, store and extract a PDF.
    Database records are committed together.
    If processing or database persistence fails after
    the physical file is stored, the file is removed.
    """
    investigation = db.execute(
        select(Investigation).where(
            Investigation.id == investigation_id
        )
    ).scalar_one_or_none()
    if investigation is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    document_id = uuid4()
    stored: StoredPDF = store_pdf(
        upload,
        storage_dir=settings.resolved_storage_dir,
        investigation_id=investigation_id,
        document_id=document_id,
        max_size_bytes=settings.max_upload_size_bytes,
    )

    try:
        extraction = extract_pdf(
            stored.absolute_path,
            max_pages=settings.max_pdf_pages,
            max_extracted_text_chars=(
                settings.max_extracted_text_chars
            ),
        )
        document = SourceDocument(
            id=document_id,
            investigation_id=investigation_id,
            document_type="pdf",
            original_filename=stored.original_filename,
            content_type=stored.content_type,
            file_size_bytes=stored.file_size_bytes,
            sha256=stored.sha256,
            storage_key=stored.storage_key,
            page_count=extraction.page_count,
            extraction_status=extraction.extraction_status,
        )
        db.add(document)
        # Ensure the source document exists before inserting
        # evidence records that reference it.
        db.flush()

        evidence_records = [
            EvidenceItem(
                investigation_id=investigation_id,
                source_document_id=document_id,
                evidence_kind="source_excerpt",
                content=page.text,
                page_number=page.page_number,
                source_start_char=page.source_start_char,
                source_end_char=page.source_end_char,
                review_status="pending",
            )
            for page in extraction.pages
        ]
        if evidence_records:
            db.add_all(evidence_records)

        db.commit()
    except Exception:
        db.rollback()
        try:
            delete_stored_file(
                settings.resolved_storage_dir,
                stored.storage_key,
            )
        except Exception:
            logger.exception(
                "Failed to clean up PDF after ingestion failure. "
                "Document ID: %s",
                document_id,
            )
        raise

    db.refresh(document)
    logger.info(
        "Document ingestion completed. "
        "Investigation ID: %s, Document ID: %s",
        investigation_id,
        document_id,
    )
    return DocumentIngestionResult(
        document=document,
        evidence_items_created=len(evidence_records),
        pages_without_text=extraction.pages_without_text,
        extracted_text_characters=(
            extraction.total_extracted_characters
        ),
    )


def get_document(
    db: Session,
    investigation_id: UUID,
    document_id: UUID,
) -> SourceDocument | None:
    """Retrieve a document belonging to an investigation."""
    statement = select(SourceDocument).where(
        SourceDocument.id == document_id,
        SourceDocument.investigation_id == investigation_id,
    )
    return db.execute(
        statement
    ).scalar_one_or_none()


def list_documents(
    db: Session,
    investigation_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[SourceDocument], int]:
    """List source documents belonging to an investigation."""
    exists = db.execute(
        select(Investigation.id).where(
            Investigation.id == investigation_id
        )
    ).scalar_one_or_none()
    if exists is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    count_statement = (
        select(func.count())
        .select_from(SourceDocument)
        .where(
            SourceDocument.investigation_id == investigation_id
        )
    )
    total = db.execute(
        count_statement
    ).scalar_one()

    statement = (
        select(SourceDocument)
        .where(
            SourceDocument.investigation_id == investigation_id
        )
        .order_by(
            SourceDocument.created_at.desc(),
            SourceDocument.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    documents = list(
        db.execute(statement).scalars().all()
    )
    return documents, total
