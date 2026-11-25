"""Text and email ingestion API endpoints."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.document import (
    DocumentUploadResponse,
    SourceDocumentRead,
)
from app.schemas.ingestion import (
    EmailIngestionRequest,
    TextIngestionRequest,
)
from app.services.exceptions import InvestigationNotFoundError
from app.services.text_ingestion_service import (
    ingest_email,
    ingest_text,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}",
    tags=["Ingestion"],
)


@router.post(
    "/ingest-text",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_text_endpoint(
    investigation_id: UUID,
    payload: TextIngestionRequest,
    db: Session = Depends(get_db),
):
    """Ingest plain text as a source document."""
    try:
        result = ingest_text(
            db=db,
            investigation_id=investigation_id,
            title=payload.title,
            content=payload.content,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    doc = result["document"]
    return DocumentUploadResponse(
        document=SourceDocumentRead.model_validate(doc),
        evidence_items_created=result[
            "evidence_items_created"
        ],
        pages_without_text=[],
        extracted_text_characters=doc.file_size_bytes,
    )


@router.post(
    "/ingest-email",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_email_endpoint(
    investigation_id: UUID,
    payload: EmailIngestionRequest,
    db: Session = Depends(get_db),
):
    """Ingest email content as a source document."""
    try:
        result = ingest_email(
            db=db,
            investigation_id=investigation_id,
            subject=payload.subject,
            sender=payload.sender,
            date=payload.date,
            body=payload.body,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    doc = result["document"]
    return DocumentUploadResponse(
        document=SourceDocumentRead.model_validate(doc),
        evidence_items_created=result[
            "evidence_items_created"
        ],
        pages_without_text=[],
        extracted_text_characters=doc.file_size_bytes,
    )
