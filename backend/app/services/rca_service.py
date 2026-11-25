import logging
import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.rca_graph import build_rca_graph
from app.core.config import Settings
from app.models.evidence_gap import EvidenceGap
from app.models.hypothesis_evidence import HypothesisEvidence
from app.models.rca_analysis_run import RCAAnalysisRun
from app.models.rca_hypothesis import RCAHypothesis
from app.models.why_step import WhyStep
from app.services.exceptions import RCAOutputValidationError
from app.services.groq_service import get_configured_model
from app.services.rca_context_service import build_rca_context


logger = logging.getLogger(__name__)


def _persist_rca_output(
    db: Session,
    *,
    run: RCAAnalysisRun,
    state: dict,
) -> None:
    """Persist validated RCA output within the caller's transaction."""
    hypotheses = state.get("hypotheses")
    details = state.get("analysis_details")

    if not isinstance(hypotheses, list) or not isinstance(details, dict):
        raise RCAOutputValidationError(
            "Validated RCA output is incomplete."
        )

    analyses = details.get("analyses")
    if not isinstance(analyses, list):
        raise RCAOutputValidationError(
            "RCA hypothesis analyses are missing."
        )

    hypothesis_ids: dict[str, UUID] = {}

    # Persist hypotheses first so dependent records can reference them.
    for item in hypotheses:
        key = item.get("hypothesis_key")
        if not key or key in hypothesis_ids:
            raise RCAOutputValidationError(
                "RCA hypothesis keys are missing or duplicated."
            )

        hypothesis_id = uuid.uuid4()
        hypothesis_ids[key] = hypothesis_id

        db.add(
            RCAHypothesis(
                id=hypothesis_id,
                investigation_id=run.investigation_id,
                analysis_run_id=run.id,
                title=item["title"],
                description=item["description"],
                causal_mechanism=item.get("causal_mechanism"),
                status="proposed",
            )
        )
        db.flush()

        for link in item.get("evidence_links", []):
            db.add(
                HypothesisEvidence(
                    id=uuid.uuid4(),
                    investigation_id=run.investigation_id,
                    hypothesis_id=hypothesis_id,
                    evidence_item_id=UUID(
                        str(link["evidence_item_id"])
                    ),
                    relationship_type=link["relationship_type"],
                    rationale=link["rationale"],
                )
            )

    # Persist each hypothesis's 5-Whys steps and specific evidence gaps.
    for analysis in analyses:
        hypothesis_key = analysis["hypothesis_key"]
        hypothesis_id = hypothesis_ids.get(hypothesis_key)

        if hypothesis_id is None:
            raise RCAOutputValidationError(
                "An RCA analysis references an unknown hypothesis."
            )

        for step in analysis.get("why_steps", []):
            evidence_id = step.get("evidence_item_id")

            db.add(
                WhyStep(
                    id=uuid.uuid4(),
                    investigation_id=run.investigation_id,
                    hypothesis_id=hypothesis_id,
                    step_number=step["step_number"],
                    question=step["question"],
                    answer=step.get("answer"),
                    answer_basis=step["answer_basis"],
                    evidence_item_id=(
                        UUID(str(evidence_id))
                        if evidence_id is not None
                        else None
                    ),
                )
            )

        for gap in analysis.get("evidence_gaps", []):
            db.add(
                EvidenceGap(
                    id=uuid.uuid4(),
                    investigation_id=run.investigation_id,
                    analysis_run_id=run.id,
                    hypothesis_id=hypothesis_id,
                    gap_type=gap["gap_type"],
                    description=gap["description"],
                    recommended_question=gap.get(
                        "recommended_question"
                    ),
                    priority=gap["priority"],
                    status="open",
                )
            )

    # Global gaps intentionally have no hypothesis association.
    for gap in details.get("global_gaps", []):
        db.add(
            EvidenceGap(
                id=uuid.uuid4(),
                investigation_id=run.investigation_id,
                analysis_run_id=run.id,
                hypothesis_id=None,
                gap_type=gap["gap_type"],
                description=gap["description"],
                recommended_question=gap.get(
                    "recommended_question"
                ),
                priority=gap["priority"],
                status="open",
            )
        )

    run.summary = details["summary"]
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)

    # One transaction for every child record and the completed status.
    db.commit()


def run_rca_analysis(
    *,
    db: Session,
    investigation_id: UUID,
    settings: Settings,
) -> dict:
    """
    Execute one versioned RCA analysis.

    The run record is committed before AI execution so failures remain
    auditable. All generated child records are committed atomically.
    """
    context = build_rca_context(
        db=db,
        investigation_id=investigation_id,
        settings=settings,
    )

    model_name = get_configured_model()

    run = RCAAnalysisRun(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        model_name=model_name,
        input_fingerprint=context.input_fingerprint,
        status="running",
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    initial_state = {
        "investigation_id": str(investigation_id),
        "run_id": str(run.id),
        "model_name": model_name,
        "evidence_items": context.evidence_items,
        "input_fingerprint": context.input_fingerprint,
    }

    try:
        graph = build_rca_graph()
        result = graph.invoke(initial_state)

        _persist_rca_output(
            db,
            run=run,
            state=result,
        )

    except Exception as exc:
        # Remove any partially inserted hypotheses, links, steps or gaps.
        db.rollback()

        try:
            failed_run = db.get(RCAAnalysisRun, run.id)
            if failed_run is not None:
                failed_run.status = "failed"
                failed_run.error_code = type(exc).__name__[:100]
                failed_run.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Unable to mark RCA run %s as failed",
                run.id,
            )

        logger.exception(
            "RCA analysis failed for investigation %s, run %s",
            investigation_id,
            run.id,
        )
        raise

    return {
        "investigation_id": str(investigation_id),
        "analysis_run_id": str(run.id),
        "status": run.status,
        "model_name": run.model_name,
        "input_fingerprint": run.input_fingerprint,
        "summary": run.summary,
        "hypotheses": result.get("hypotheses", []),
        "analysis_details": result.get("analysis_details", {}),
        "warnings": (
            result.get("hypothesis_generation", {}).get("warnings", [])
            + result.get("analysis_details", {}).get("warnings", [])
        ),
    }
