"""RCA analysis API endpoints."""

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
from app.models.evidence_gap import EvidenceGap
from app.models.hypothesis_evidence import HypothesisEvidence
from app.models.investigation import Investigation
from app.models.rca_analysis_run import RCAAnalysisRun
from app.models.rca_hypothesis import RCAHypothesis
from app.models.why_step import WhyStep
from app.schemas.rca_response import (
    EvidenceGapRead,
    HypothesisDetailRead,
    HypothesisEvidenceLinkRead,
    RCARunDetailRead,
    RCARunListResponse,
    RCARunSummaryRead,
    WhyStepRead,
)
from app.services.exceptions import (
    InvestigationNotFoundError,
    NoRCAEvidenceError,
    RCAContextLimitError,
    RCAOutputValidationError,
)
from app.services.groq_service import (
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    StructuredOutputError,
)
from app.services.rca_service import run_rca_analysis

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}/rca",
    tags=["RCA Analysis"],
)


def _load_run_detail(
    db: Session,
    run: RCAAnalysisRun,
) -> RCARunDetailRead:
    """Build a full RCA run detail response from DB records."""
    hypotheses_rows = (
        db.execute(
            select(RCAHypothesis)
            .where(
                RCAHypothesis.analysis_run_id == run.id,
                RCAHypothesis.investigation_id
                == run.investigation_id,
            )
            .order_by(RCAHypothesis.created_at.asc())
        )
        .scalars()
        .all()
    )

    hypothesis_details = []
    for hyp in hypotheses_rows:
        links = (
            db.execute(
                select(HypothesisEvidence)
                .where(
                    HypothesisEvidence.hypothesis_id == hyp.id,
                    HypothesisEvidence.investigation_id
                    == hyp.investigation_id,
                )
                .order_by(HypothesisEvidence.created_at.asc())
            )
            .scalars()
            .all()
        )

        steps = (
            db.execute(
                select(WhyStep)
                .where(
                    WhyStep.hypothesis_id == hyp.id,
                    WhyStep.investigation_id
                    == hyp.investigation_id,
                )
                .order_by(WhyStep.step_number.asc())
            )
            .scalars()
            .all()
        )

        hyp_gaps = (
            db.execute(
                select(EvidenceGap)
                .where(
                    EvidenceGap.hypothesis_id == hyp.id,
                    EvidenceGap.investigation_id
                    == hyp.investigation_id,
                )
                .order_by(EvidenceGap.created_at.asc())
            )
            .scalars()
            .all()
        )

        hypothesis_details.append(
            HypothesisDetailRead(
                id=hyp.id,
                investigation_id=hyp.investigation_id,
                analysis_run_id=hyp.analysis_run_id,
                title=hyp.title,
                description=hyp.description,
                causal_mechanism=hyp.causal_mechanism,
                status=hyp.status,
                review_note=hyp.review_note,
                reviewed_at=hyp.reviewed_at,
                created_at=hyp.created_at,
                updated_at=hyp.updated_at,
                evidence_links=[
                    HypothesisEvidenceLinkRead.model_validate(l)
                    for l in links
                ],
                why_steps=[
                    WhyStepRead.model_validate(s)
                    for s in steps
                ],
                evidence_gaps=[
                    EvidenceGapRead.model_validate(g)
                    for g in hyp_gaps
                ],
            )
        )

    global_gaps = (
        db.execute(
            select(EvidenceGap)
            .where(
                EvidenceGap.analysis_run_id == run.id,
                EvidenceGap.investigation_id
                == run.investigation_id,
                EvidenceGap.hypothesis_id.is_(None),
            )
            .order_by(EvidenceGap.created_at.asc())
        )
        .scalars()
        .all()
    )

    return RCARunDetailRead(
        id=run.id,
        investigation_id=run.investigation_id,
        model_name=run.model_name,
        input_fingerprint=run.input_fingerprint,
        status=run.status,
        summary=run.summary,
        error_code=run.error_code,
        created_at=run.created_at,
        completed_at=run.completed_at,
        hypotheses=hypothesis_details,
        global_gaps=[
            EvidenceGapRead.model_validate(g)
            for g in global_gaps
        ],
    )


@router.post(
    "",
    response_model=RCARunDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def start_rca_analysis(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Execute a new RCA analysis run.
    Generated hypotheses are always 'proposed' status.
    """
    settings = get_settings()
    try:
        result = run_rca_analysis(
            db=db,
            investigation_id=investigation_id,
            settings=settings,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NoRCAEvidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RCAContextLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except RCAOutputValidationError as exc:
        logger.exception(
            "RCA output validation failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AIModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (AIConnectionError, StructuredOutputError) as exc:
        logger.exception(
            "RCA AI call failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis service failed.",
        ) from exc

    # Reload from DB for consistent response
    run_id = UUID(result["analysis_run_id"])
    run = db.get(RCAAnalysisRun, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load completed RCA run.",
        )
    return _load_run_detail(db, run)


@router.get(
    "",
    response_model=RCARunListResponse,
)
def list_rca_runs(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """List all RCA analysis runs for an investigation."""
    if db.get(Investigation, investigation_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        )

    runs = (
        db.execute(
            select(RCAAnalysisRun)
            .where(
                RCAAnalysisRun.investigation_id
                == investigation_id
            )
            .order_by(RCAAnalysisRun.created_at.desc())
        )
        .scalars()
        .all()
    )

    total = db.execute(
        select(func.count())
        .select_from(RCAAnalysisRun)
        .where(
            RCAAnalysisRun.investigation_id
            == investigation_id
        )
    ).scalar_one()

    return RCARunListResponse(
        items=[
            RCARunSummaryRead.model_validate(r)
            for r in runs
        ],
        total=total,
    )


@router.get(
    "/{run_id}",
    response_model=RCARunDetailRead,
)
def get_rca_run(
    investigation_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
):
    """Get full RCA run details including hypotheses and gaps."""
    run = db.execute(
        select(RCAAnalysisRun).where(
            RCAAnalysisRun.id == run_id,
            RCAAnalysisRun.investigation_id
            == investigation_id,
        )
    ).scalar_one_or_none()

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RCA analysis run not found.",
        )

    return _load_run_detail(db, run)
