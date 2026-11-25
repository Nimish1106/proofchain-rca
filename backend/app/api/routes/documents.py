import logging
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.evidence_item import EvidenceItem
from app.schemas.document import (
    DocumentUploadResponse,
    SourceDocumentListResponse,
    SourceDocumentRead,
)
from app.services.document_extraction import (
    EncryptedPDFError,
    InvalidPDFError,
    PDFPageLimitExceeded,
    PDFTextLimitExceeded,
)
from app.services.document_service import (
    get_document,
    ingest_pdf,
    list_documents,
)
from app.services.document_storage import (
    DocumentStorageError,
    InvalidDocumentUpload,
    UploadSizeLimitExceeded,
    resolve_storage_path,
)
from app.services.exceptions import InvestigationNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}/documents",
    tags=["Documents"],
)


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    investigation_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload and ingest a PDF for an investigation.
    The file is stored privately, extracted page by page,
    and persisted with its source excerpts.
    """
    settings = get_settings()
    try:
        result = ingest_pdf(
            db=db,
            investigation_id=investigation_id,
            upload=file,
            settings=settings,
        )
        return DocumentUploadResponse(
            document=result.document,
            evidence_items_created=(
                result.evidence_items_created
            ),
            pages_without_text=result.pages_without_text,
            extracted_text_characters=(
                result.extracted_text_characters
            ),
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UploadSizeLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except (PDFPageLimitExceeded, PDFTextLimitExceeded) as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except InvalidDocumentUpload as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except (EncryptedPDFError, InvalidPDFError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except DocumentStorageError as exc:
        logger.exception(
            "Document storage failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document storage failed.",
        ) from exc
    finally:
        file.file.close()


@router.get(
    "",
    response_model=SourceDocumentListResponse,
)
def get_documents(
    investigation_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List documents belonging to an investigation."""
    try:
        documents, total = list_documents(
            db=db,
            investigation_id=investigation_id,
            limit=limit,
            offset=offset,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return SourceDocumentListResponse(
        items=documents,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=SourceDocumentRead,
)
def get_document_details(
    investigation_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve document metadata."""
    document = get_document(
        db=db,
        investigation_id=investigation_id,
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


@router.get(
    "/{document_id}/download",
    response_class=FileResponse,
)
def download_document(
    investigation_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Download the original PDF using a validated storage key."""
    document = get_document(
        db=db,
        investigation_id=investigation_id,
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.document_type in ("text", "email"):
        excerpts = (
            db.execute(
                select(EvidenceItem)
                .where(
                    EvidenceItem.source_document_id == document_id,
                    EvidenceItem.investigation_id == investigation_id,
                    EvidenceItem.evidence_kind == "source_excerpt",
                )
                .order_by(EvidenceItem.page_number.asc().nulls_last())
            )
            .scalars()
            .all()
        )
        text_body = "\n\n".join(e.content for e in excerpts)
        safe_name = Path(document.original_filename).name
        return PlainTextResponse(
            content=text_body,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.txt"'
            },
        )

    settings = get_settings()
    try:
        path = resolve_storage_path(
            settings.resolved_storage_dir,
            document.storage_key,
        )
    except DocumentStorageError as exc:
        logger.exception(
            "Invalid storage key for document %s",
            document_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored document path is invalid.",
        ) from exc

    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored document file is unavailable.",
        )

    return FileResponse(
        path=path,
        filename=Path(document.original_filename).name,
        media_type="application/pdf",
    )


@router.get("/{document_id}/content")
def get_document_content(
    investigation_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
):
    """Return extracted source excerpts page-by-page for document preview."""
    document = get_document(
        db=db,
        investigation_id=investigation_id,
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    excerpts = (
        db.execute(
            select(EvidenceItem)
            .where(
                EvidenceItem.source_document_id == document_id,
                EvidenceItem.investigation_id == investigation_id,
                EvidenceItem.evidence_kind == "source_excerpt",
            )
            .order_by(EvidenceItem.page_number.asc().nulls_last())
        )
        .scalars()
        .all()
    )

    return {
        "document_id": str(document.id),
        "document_type": document.document_type,
        "original_filename": document.original_filename,
        "page_count": document.page_count,
        "extraction_status": document.extraction_status,
        "pages": [
            {
                "evidence_id": str(e.id),
                "page_number": e.page_number,
                "content": e.content,
            }
            for e in excerpts
        ],
    }
