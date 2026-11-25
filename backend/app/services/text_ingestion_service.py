"""Text and email ingestion service."""

import hashlib
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.models.source_document import SourceDocument
from app.services.exceptions import InvestigationNotFoundError


def _sha256(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def ingest_text(
    *,
    db: Session,
    investigation_id: UUID,
    title: str,
    content: str,
) -> dict:
    """Ingest plain text content as a source document."""
    investigation = db.get(
        Investigation, investigation_id
    )
    if investigation is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    text_hash = _sha256(content)

    document = SourceDocument(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        document_type="text",
        original_filename=title,
        content_type="text/plain",
        file_size_bytes=len(content.encode("utf-8")),
        sha256=text_hash,
        storage_key=f"text/{investigation_id}/{uuid.uuid4()}.txt",
        page_count=1,
        extraction_status="text_extracted",
    )
    db.add(document)
    db.flush()

    evidence = EvidenceItem(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        source_document_id=document.id,
        evidence_kind="source_excerpt",
        content=content,
        page_number=1,
    )
    db.add(evidence)
    db.commit()
    db.refresh(document)

    return {
        "document": document,
        "evidence_items_created": 1,
    }


def ingest_email(
    *,
    db: Session,
    investigation_id: UUID,
    subject: str,
    sender: str,
    date: str | None,
    body: str,
) -> dict:
    """Ingest email content as a source document."""
    investigation = db.get(
        Investigation, investigation_id
    )
    if investigation is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    # Compose full email text
    header = f"From: {sender}\nSubject: {subject}"
    if date:
        header += f"\nDate: {date}"
    full_text = f"{header}\n\n{body}"

    text_hash = _sha256(full_text)
    filename = f"email_{subject[:50].replace(' ', '_')}"

    document = SourceDocument(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        document_type="email",
        original_filename=filename,
        content_type="message/rfc822",
        file_size_bytes=len(full_text.encode("utf-8")),
        sha256=text_hash,
        storage_key=f"email/{investigation_id}/{uuid.uuid4()}.eml",
        page_count=1,
        extraction_status="text_extracted",
    )
    db.add(document)
    db.flush()

    evidence = EvidenceItem(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        source_document_id=document.id,
        evidence_kind="source_excerpt",
        content=full_text,
        page_number=1,
    )
    db.add(evidence)
    db.commit()
    db.refresh(document)

    return {
        "document": document,
        "evidence_items_created": 1,
    }
