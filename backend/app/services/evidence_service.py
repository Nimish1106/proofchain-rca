from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.services.exceptions import InvestigationNotFoundError


def list_evidence(
    db: Session,
    investigation_id: UUID,
    limit: int = 20,
    offset: int = 0,
    document_id: UUID | None = None,
) -> tuple[list[EvidenceItem], int]:
    """List evidence belonging to an investigation."""
    investigation_exists = db.execute(
        select(Investigation.id).where(
            Investigation.id == investigation_id
        )
    ).scalar_one_or_none()
    if investigation_exists is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    filters = [
        EvidenceItem.investigation_id == investigation_id
    ]
    if document_id is not None:
        filters.append(
            EvidenceItem.source_document_id == document_id
        )

    count_statement = (
        select(func.count())
        .select_from(EvidenceItem)
        .where(*filters)
    )
    total = db.execute(
        count_statement
    ).scalar_one()

    statement = (
        select(EvidenceItem)
        .where(*filters)
        .order_by(
            EvidenceItem.created_at.asc(),
            EvidenceItem.page_number.asc().nulls_last(),
            EvidenceItem.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    items = list(
        db.execute(statement).scalars().all()
    )
    return items, total


def get_evidence(
    db: Session,
    investigation_id: UUID,
    evidence_id: UUID,
) -> EvidenceItem | None:
    """Retrieve one evidence record within an investigation."""
    statement = select(EvidenceItem).where(
        EvidenceItem.id == evidence_id,
        EvidenceItem.investigation_id == investigation_id,
    )
    return db.execute(
        statement
    ).scalar_one_or_none()
