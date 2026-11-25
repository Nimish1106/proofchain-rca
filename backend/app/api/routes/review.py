"""Human review endpoints for evidence, hypotheses, why-steps, and gaps."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.evidence_gap import EvidenceGap
from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.models.rca_hypothesis import RCAHypothesis
from app.models.why_step import WhyStep
from app.schemas.evidence import EvidenceRead
from app.schemas.rca_response import (
    EvidenceGapRead,
    HypothesisRead,
    EvidenceReviewUpdate,
    EvidenceGapUpdate,
    HypothesisStatusUpdate,
    WhyStepRead,
    WhyStepUpdate,
)
from app.utils.date_utils import (
    parse_affected_quantity,
    parse_incident_date,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}",
    tags=["Human Review"],
)


@router.patch(
    "/evidence/{evidence_id}",
    response_model=EvidenceRead,
)
def review_evidence(
    investigation_id: UUID,
    evidence_id: UUID,
    payload: EvidenceReviewUpdate,
    db: Session = Depends(get_db),
):
    """Accept or reject an evidence item."""
    evidence = db.execute(
        select(EvidenceItem).where(
            EvidenceItem.id == evidence_id,
            EvidenceItem.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found.",
        )

    evidence.review_status = payload.review_status

    if (
        payload.apply_to_investigation
        and payload.review_status == "accepted"
        and evidence.field_name
        and evidence.extracted_value is not None
    ):
        investigation = db.get(Investigation, investigation_id)
        if investigation is not None and hasattr(investigation, evidence.field_name):
            val: object = evidence.extracted_value
            if evidence.field_name == "incident_date":
                try:
                    val = parse_incident_date(str(val))
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=str(exc),
                    ) from exc
            elif evidence.field_name == "affected_quantity":
                try:
                    val = parse_affected_quantity(str(val))
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=str(exc),
                    ) from exc
            setattr(investigation, evidence.field_name, val)

    db.commit()
    db.refresh(evidence)
    return evidence


@router.patch(
    "/hypotheses/{hypothesis_id}",
    response_model=HypothesisRead,
)
def review_hypothesis(
    investigation_id: UUID,
    hypothesis_id: UUID,
    payload: HypothesisStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the review status of a hypothesis."""
    hypothesis = db.execute(
        select(RCAHypothesis).where(
            RCAHypothesis.id == hypothesis_id,
            RCAHypothesis.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if hypothesis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hypothesis not found.",
        )

    hypothesis.status = payload.status
    if payload.review_note is not None:
        hypothesis.review_note = payload.review_note
    hypothesis.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hypothesis)
    return hypothesis


@router.patch(
    "/why-steps/{step_id}",
    response_model=WhyStepRead,
)
def edit_why_step(
    investigation_id: UUID,
    step_id: UUID,
    payload: WhyStepUpdate,
    db: Session = Depends(get_db),
):
    """Edit a 5-Whys question or answer."""
    step = db.execute(
        select(WhyStep).where(
            WhyStep.id == step_id,
            WhyStep.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Why step not found.",
        )

    if payload.question is not None:
        step.question = payload.question.strip()
    if payload.answer is not None:
        cleaned_answer = payload.answer.strip()
        if step.answer_basis == "source_supported" and not cleaned_answer:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Source-supported step answer cannot be empty.",
            )
        step.answer = cleaned_answer or None
    db.commit()
    db.refresh(step)
    return step


@router.patch(
    "/evidence-gaps/{gap_id}",
    response_model=EvidenceGapRead,
)
def resolve_evidence_gap(
    investigation_id: UUID,
    gap_id: UUID,
    payload: EvidenceGapUpdate,
    db: Session = Depends(get_db),
):
    """Mark an evidence gap as addressed or waived."""
    gap = db.execute(
        select(EvidenceGap).where(
            EvidenceGap.id == gap_id,
            EvidenceGap.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if gap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence gap not found.",
        )

    gap.status = payload.status
    if payload.resolution_note is not None:
        gap.resolution_note = payload.resolution_note
    if payload.status in ("addressed", "waived"):
        gap.resolved_at = datetime.now(timezone.utc)
    else:
        gap.resolved_at = None
    db.commit()
    db.refresh(gap)
    return gap
