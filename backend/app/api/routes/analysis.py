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
from app.schemas.extraction_run import ExtractionRunResponse
from app.services.exceptions import (
    InvestigationNotFoundError,
    NoSourceDocumentsError,
)
from app.services.extraction_service import (
    run_document_extraction,
)
from app.services.groq_service import (
    AIConfigurationError,
    AIConnectionError,
    AIModelUnavailableError,
    StructuredOutputError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/investigations",
    tags=["AI Analysis"],
)


@router.post(
    "/{investigation_id}/extract-facts",
    response_model=ExtractionRunResponse,
    status_code=status.HTTP_200_OK,
)
def extract_investigation_facts(
    investigation_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Execute source-grounded AI fact extraction.
    Extracted facts are stored as pending human review.
    They do not automatically overwrite investigation fields.
    """
    settings = get_settings()
    try:
        result = run_document_extraction(
            db=db,
            investigation_id=investigation_id,
            settings=settings,
        )
        return ExtractionRunResponse(
            investigation_id=investigation_id,
            status=result.get(
                "workflow_status",
                "completed",
            ),
            summaries=result.get("summaries", []),
            extracted_facts=result.get(
                "persisted_facts", []
            ),
            validated_fact_count=len(
                result.get("validated_facts", [])
            ),
            new_facts_count=result.get(
                "new_facts_count", 0
            ),
            duplicate_facts_count=result.get(
                "duplicate_facts_count", 0
            ),
            rejected_facts=result.get(
                "rejected_facts", []
            ),
            field_conflicts=result.get(
                "field_conflicts", []
            ),
            warnings=result.get("warnings", []),
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NoSourceDocumentsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    except AIConnectionError as exc:
        logger.exception(
            "Groq extraction failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI extraction service failed.",
        ) from exc
    except StructuredOutputError as exc:
        logger.exception(
            "Structured extraction failed for investigation %s",
            investigation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "AI returned an invalid structured response."
            ),
        ) from exc
