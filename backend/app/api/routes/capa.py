"""CAPA API endpoints."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.capa_recommendation import CAPARecommendation
from app.models.investigation import Investigation
from app.schemas.capa import (
    CAPAListResponse,
    CAPARead,
    CAPAStatusUpdate,
)
from app.services.capa_service import (
    generate_capa_recommendations,
)
from app.services.exceptions import (
    InvestigationNotFoundError,
    RCAOutputValidationError,
)
from app.services.groq_service import (
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    StructuredOutputError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}/capa",
    tags=["CAPA"],
)


@router.post(
    "",
    response_model=CAPAListResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_capa(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """Generate CAPA recommendations from the latest RCA run."""
    settings = get_settings()
    try:
        result = generate_capa_recommendations(
            db=db,
            investigation_id=investigation_id,
            settings=settings,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RCAOutputValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (
        AIConnectionError,
        AIModelUnavailableError,
        StructuredOutputError,
    ) as exc:
        logger.exception(
            "CAPA generation failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI CAPA generation failed.",
        ) from exc

    return CAPAListResponse(
        items=[
            CAPARead.model_validate(c)
            for c in result["recommendations"]
        ],
        total=len(result["recommendations"]),
    )


@router.get(
    "",
    response_model=CAPAListResponse,
)
def list_capa(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """List CAPA recommendations for an investigation."""
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    capas = (
        db.execute(
            select(CAPARecommendation)
            .where(
                CAPARecommendation.investigation_id
                == investigation_id
            )
            .order_by(
                CAPARecommendation.created_at.desc()
            )
        )
        .scalars()
        .all()
    )

    total = db.execute(
        select(func.count())
        .select_from(CAPARecommendation)
        .where(
            CAPARecommendation.investigation_id
            == investigation_id
        )
    ).scalar_one()

    return CAPAListResponse(
        items=[
            CAPARead.model_validate(c)
            for c in capas
        ],
        total=total,
    )


@router.patch(
    "/{capa_id}",
    response_model=CAPARead,
)
def update_capa_status(
    investigation_id: UUID,
    capa_id: UUID,
    payload: CAPAStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the status of a CAPA recommendation."""
    capa = db.execute(
        select(CAPARecommendation).where(
            CAPARecommendation.id == capa_id,
            CAPARecommendation.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if capa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CAPA recommendation not found.",
        )

    capa.status = payload.status
    if payload.review_note is not None:
        capa.review_note = payload.review_note
    db.commit()
    db.refresh(capa)
    return capa
