"""CAPA generation service using the two-stage CAPA LangGraph workflow."""

import logging
import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.capa_graph import build_capa_graph
from app.core.config import Settings
from app.models.capa_recommendation import CAPARecommendation
from app.models.evidence_item import EvidenceItem
from app.models.hypothesis_evidence import HypothesisEvidence
from app.models.investigation import Investigation
from app.models.rca_analysis_run import RCAAnalysisRun
from app.models.rca_hypothesis import RCAHypothesis
from app.models.why_step import WhyStep
from app.schemas.capa import CAPAGenerationOutput
from app.services.exceptions import (
    InvestigationNotFoundError,
    RCAOutputValidationError,
)

logger = logging.getLogger(__name__)


def generate_capa_recommendations(
    *,
    db: Session,
    investigation_id: UUID,
    settings: Settings,
) -> dict:
    """
    Generate and stress-test CAPA recommendations from the latest completed RCA run.
    """
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise InvestigationNotFoundError("Investigation not found.")

    run = db.execute(
        select(RCAAnalysisRun)
        .where(
            RCAAnalysisRun.investigation_id == investigation_id,
            RCAAnalysisRun.status == "completed",
        )
        .order_by(RCAAnalysisRun.created_at.desc())
    ).scalar_one_or_none()

    if run is None:
        raise RCAOutputValidationError(
            "No completed RCA analysis run exists. Run an RCA analysis first."
        )

    hypotheses = (
        db.execute(
            select(RCAHypothesis)
            .where(
                RCAHypothesis.analysis_run_id == run.id,
                RCAHypothesis.investigation_id == investigation_id,
            )
            .order_by(RCAHypothesis.created_at.asc())
        )
        .scalars()
        .all()
    )

    if not hypotheses:
        raise RCAOutputValidationError(
            "The latest RCA run produced no hypotheses."
        )

    eligible = [
        h for h in hypotheses if h.status != "rejected"
    ] or hypotheses

    hypotheses_context = []
    hypothesis_key_map: dict[str, UUID] = {}

    for idx, hyp in enumerate(eligible[:3], 1):
        key = f"H{idx}"
        hypothesis_key_map[key] = hyp.id

        links_rows = db.execute(
            select(HypothesisEvidence, EvidenceItem)
            .join(
                EvidenceItem,
                EvidenceItem.id == HypothesisEvidence.evidence_item_id,
            )
            .where(
                HypothesisEvidence.hypothesis_id == hyp.id,
                HypothesisEvidence.investigation_id == investigation_id,
            )
        ).all()

        why_steps = (
            db.execute(
                select(WhyStep)
                .where(
                    WhyStep.hypothesis_id == hyp.id,
                    WhyStep.investigation_id == investigation_id,
                )
                .order_by(WhyStep.step_number.asc())
            )
            .scalars()
            .all()
        )

        hypotheses_context.append(
            {
                "hypothesis_key": key,
                "title": hyp.title,
                "description": hyp.description,
                "causal_mechanism": hyp.causal_mechanism,
                "status": hyp.status,
                "evidence_links": [
                    {
                        "relationship_type": link.relationship_type,
                        "rationale": link.rationale,
                        "content": ev.content,
                    }
                    for link, ev in links_rows
                ],
                "why_steps": [
                    {
                        "step_number": step.step_number,
                        "question": step.question,
                        "answer": step.answer,
                        "answer_basis": step.answer_basis,
                    }
                    for step in why_steps
                ],
            }
        )

    inv_summary = "\n".join(
        filter(
            None,
            [
                f"Title: {investigation.title}",
                f"Product: {investigation.product_name}"
                if investigation.product_name
                else None,
                f"Batch: {investigation.batch_number}"
                if investigation.batch_number
                else None,
                f"Process Stage: {investigation.process_stage}"
                if investigation.process_stage
                else None,
                f"Description: {investigation.incident_description}"
                if investigation.incident_description
                else None,
                f"Immediate Containment: {investigation.immediate_containment}"
                if investigation.immediate_containment
                else None,
            ],
        )
    )

    graph = build_capa_graph()
    result = graph.invoke(
        {
            "investigation_id": str(investigation_id),
            "investigation_summary": inv_summary,
            "rca_summary": run.summary,
            "hypotheses_context": hypotheses_context,
        }
    )

    final_capa = result.get("final_capa") or result.get("draft_capa")
    parsed = CAPAGenerationOutput.model_validate(final_capa)

    created_capas = []
    for rec in parsed.recommendations:
        hypothesis_id = hypothesis_key_map.get(rec.hypothesis_key)
        if hypothesis_id is None:
            continue

        capa = CAPARecommendation(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            hypothesis_id=hypothesis_id,
            capa_type=rec.capa_type,
            title=rec.title,
            description=rec.description,
            expected_outcome=rec.expected_outcome,
            verification_method=rec.verification_method,
            effectiveness_criteria=rec.effectiveness_criteria,
            priority=rec.priority,
            residual_risk=rec.residual_risk,
            status="proposed",
        )
        db.add(capa)
        created_capas.append(capa)

    db.commit()
    for capa in created_capas:
        db.refresh(capa)

    return {
        "investigation_id": str(investigation_id),
        "analysis_run_id": str(run.id),
        "recommendations": created_capas,
        "summary": parsed.summary,
        "warnings": result.get("warnings", parsed.warnings),
    }
