"""AI Copilot API endpoints."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.schemas.copilot import (
    CopilotApplyEditsRequest,
    CopilotRequest,
    CopilotResponse,
)
from app.schemas.investigation import InvestigationRead
from app.services.copilot_service import (
    apply_copilot_edits,
    run_copilot,
)
from app.services.exceptions import InvestigationNotFoundError
from app.services.groq_service import (
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    StructuredOutputError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations/{investigation_id}/copilot",
    tags=["AI Copilot"],
)


@router.post(
    "",
    response_model=CopilotResponse,
)
def ask_copilot(
    investigation_id: UUID,
    request: CopilotRequest,
    db: Session = Depends(get_db),
):
    """Ask the AI Copilot a question or request targeted field edits."""
    settings = get_settings()
    try:
        return run_copilot(
            db=db,
            investigation_id=investigation_id,
            request=request,
            settings=settings,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
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
            "Copilot request failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI Copilot service failed.",
        ) from exc


@router.post(
    "/apply",
    response_model=InvestigationRead,
)
def apply_copilot_field_edits(
    investigation_id: UUID,
    payload: CopilotApplyEditsRequest,
    db: Session = Depends(get_db),
):
    """Apply user-approved Copilot field edits while preserving unrelated fields."""
    try:
        return apply_copilot_edits(
            db=db,
            investigation_id=investigation_id,
            payload=payload,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
