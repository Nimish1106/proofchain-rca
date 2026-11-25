from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.state import ExtractionState
from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.models.source_document import SourceDocument
from app.services.exceptions import (
    InvestigationNotFoundError,
    NoSourceDocumentsError,
)


def load_sources(
    state: ExtractionState,
    db: Session,
) -> dict:
    """
    Load original source pages for one investigation.
    Only original source excerpts are loaded.
    Previously generated AI claims are excluded.
    """
    investigation_id = UUID(state["investigation_id"])
    investigation = db.get(
        Investigation,
        investigation_id,
    )
    if investigation is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    documents = list(
        db.execute(
            select(SourceDocument)
            .where(
                SourceDocument.investigation_id
                == investigation_id
            )
            .order_by(
                SourceDocument.created_at.asc(),
                SourceDocument.id.asc(),
            )
        )
        .scalars()
        .all()
    )
    if not documents:
        raise NoSourceDocumentsError(
            "Upload at least one source document "
            "before running extraction."
        )

    statement = (
        select(
            EvidenceItem,
            SourceDocument.original_filename,
        )
        .join(
            SourceDocument,
            SourceDocument.id
            == EvidenceItem.source_document_id,
        )
        .where(
            EvidenceItem.investigation_id == investigation_id,
            EvidenceItem.evidence_kind == "source_excerpt",
        )
        .order_by(
            SourceDocument.created_at.asc(),
            SourceDocument.id.asc(),
            EvidenceItem.page_number.asc().nulls_last(),
            EvidenceItem.id.asc(),
        )
    )
    rows = db.execute(statement).all()

    source_pages = []
    for evidence, filename in rows:
        source_pages.append(
            {
                "source_document_id": str(
                    evidence.source_document_id
                ),
                "original_filename": filename,
                "page_number": evidence.page_number,
                "text": evidence.content,
                "source_start_char": (
                    evidence.source_start_char or 0
                ),
            }
        )

    warnings = []
    for document in documents:
        if document.extraction_status == "needs_ocr":
            warnings.append(
                f"{document.original_filename}: "
                "No machine-readable text was found. "
                "OCR is required before AI extraction."
            )
        elif document.extraction_status == "partial_text":
            warnings.append(
                f"{document.original_filename}: "
                "Some pages did not contain extractable text."
            )

    if not source_pages:
        warnings.append(
            "No machine-readable source excerpts are available."
        )

    return {
        "source_pages": source_pages,
        "warnings": warnings,
    }
