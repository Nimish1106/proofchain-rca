from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.evidence import (
    EvidenceListResponse,
    EvidenceRead,
)
from app.services.evidence_service import (
    get_evidence,
    list_evidence,
)
from app.services.exceptions import InvestigationNotFoundError

router = APIRouter(
    prefix="/investigations/{investigation_id}/evidence",
    tags=["Evidence"],
)


@router.get(
    "",
    response_model=EvidenceListResponse,
)
def get_evidence_list(
    investigation_id: UUID,
    document_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve evidence records for an investigation."""
    try:
        items, total = list_evidence(
            db=db,
            investigation_id=investigation_id,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return EvidenceListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{evidence_id}",
    response_model=EvidenceRead,
)
def get_evidence_details(
    investigation_id: UUID,
    evidence_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve one evidence item."""
    evidence = get_evidence(
        db=db,
        investigation_id=investigation_id,
        evidence_id=evidence_id,
    )
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found.",
        )
    return evidence
