from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationListResponse,
    InvestigationRead,
    InvestigationUpdate,
)
from app.services.investigation_service import (
    create_investigation,
    get_investigation,
    list_investigations,
    update_investigation,
)

router = APIRouter(
    prefix="/investigations",
    tags=["Investigations"],
)


@router.post(
    "",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_investigation_endpoint(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
):
    """Create a new investigation."""
    return create_investigation(db, payload)


@router.get(
    "",
    response_model=InvestigationListResponse,
)
def list_investigations_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List investigations with pagination."""
    items, total = list_investigations(
        db=db,
        limit=limit,
        offset=offset,
    )
    return InvestigationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationRead,
)
def get_investigation_endpoint(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve an investigation by UUID."""
    investigation = get_investigation(
        db,
        investigation_id,
    )
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )
    return investigation


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationRead,
)
def update_investigation_endpoint(
    investigation_id: UUID,
    payload: InvestigationUpdate,
    db: Session = Depends(get_db),
):
    """Update selected investigation fields."""
    investigation = get_investigation(
        db,
        investigation_id,
    )
    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )
    return update_investigation(
        db=db,
        investigation=investigation,
        payload=payload,
    )
