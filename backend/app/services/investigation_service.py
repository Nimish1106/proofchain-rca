from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationUpdate,
)


def create_investigation(
    db: Session,
    payload: InvestigationCreate,
) -> Investigation:
    """Create and persist a new investigation."""
    investigation = Investigation(
        **payload.model_dump()
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


def get_investigation(
    db: Session,
    investigation_id: UUID,
) -> Investigation | None:
    """Retrieve one investigation by UUID."""
    statement = select(Investigation).where(
        Investigation.id == investigation_id
    )
    return db.execute(statement).scalar_one_or_none()


def list_investigations(
    db: Session,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Investigation], int]:
    """Retrieve investigations with pagination."""
    count_statement = select(
        func.count()
    ).select_from(Investigation)
    total = db.execute(
        count_statement
    ).scalar_one()

    statement = (
        select(Investigation)
        .order_by(
            Investigation.created_at.desc(),
            Investigation.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    items = list(
        db.execute(statement).scalars().all()
    )
    return items, total


def update_investigation(
    db: Session,
    investigation: Investigation,
    payload: InvestigationUpdate,
) -> Investigation:
    """
    Update only explicitly supplied fields.
    Unmodified database fields remain untouched.
    """
    updates = payload.model_dump(
        exclude_unset=True
    )
    for field, value in updates.items():
        setattr(investigation, field, value)

    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation
