from enum import Enum

from pydantic import ValidationError

from app.agents.nodes.rca_schema_utils import get_typed_list
from app.agents.rca_state import RCAState
from app.schemas.rca_analysis import (
    EvidenceGapProposal,
    HypothesisAnalysisProposal,
    HypothesisEvidenceProposal,
    HypothesisGenerationOutput,
    HypothesisProposal,
    RCAAnalysisDetailsOutput,
    WhyStepProposal,
)
from app.services.exceptions import RCAOutputValidationError


def _value(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def validate_evidence_reference(
    evidence_item_id: str | None,
    evidence_by_id: dict[str, dict],
    *,
    purpose: str,
) -> dict:
    """Resolve a reference and enforce review-state restrictions."""
    if not evidence_item_id:
        raise RCAOutputValidationError(
            f"An evidence reference is required for {purpose}."
        )

    evidence = evidence_by_id.get(evidence_item_id)
    if evidence is None:
        raise RCAOutputValidationError(
            f"Unknown evidence reference in {purpose}: {evidence_item_id}"
        )

    review_status = _value(evidence.get("review_status"))
    evidence_kind = _value(evidence.get("evidence_kind"))

    if evidence_kind == "extracted_fact" and review_status == "rejected":
        raise RCAOutputValidationError(
            f"Rejected extracted evidence cannot be cited for {purpose}."
        )

    if (
        evidence_kind == "extracted_fact"
        and review_status == "pending"
        and purpose in {"supports", "contradicts", "source_supported"}
    ):
        raise RCAOutputValidationError(
            f"Pending extracted evidence cannot be used as {purpose}."
        )

    return evidence


def validate_rca(state: RCAState) -> dict:
    """Validate every hypothesis, analysis entry, and evidence reference."""
    evidence_items = state.get("evidence_items", [])
    keyed_hypotheses = state.get("hypotheses", [])
    raw_generation = state.get("hypothesis_generation")
    raw_details = state.get("analysis_details")

    if not evidence_items:
        raise RCAOutputValidationError("RCA evidence is missing.")

    if raw_generation is None or raw_details is None:
        raise RCAOutputValidationError(
            "RCA reasoning output is incomplete."
        )

    evidence_by_id: dict[str, dict] = {}
    for evidence in evidence_items:
        evidence_id = evidence.get("evidence_id")
        if not evidence_id:
            raise RCAOutputValidationError(
                "An evidence record has no evidence_id."
            )
        if evidence_id in evidence_by_id:
            raise RCAOutputValidationError(
                "The supplied evidence context contains duplicate IDs."
            )
        evidence_by_id[evidence_id] = evidence

    try:
        generation = HypothesisGenerationOutput.model_validate(
            raw_generation
        )
        details = RCAAnalysisDetailsOutput.model_validate(raw_details)
    except ValidationError as exc:
        raise RCAOutputValidationError(
            "RCA output failed schema validation."
        ) from exc

    proposals = get_typed_list(generation, HypothesisProposal)
    if len(proposals) > 3:
        raise RCAOutputValidationError(
            "RCA output contains more than three hypotheses."
        )

    if len(keyed_hypotheses) != len(proposals):
        raise RCAOutputValidationError(
            "The keyed hypothesis list does not match generated hypotheses."
        )

    expected_keys = [f"H{index}" for index in range(1, len(proposals) + 1)]
    actual_keys = [
        hypothesis.get("hypothesis_key")
        for hypothesis in keyed_hypotheses
    ]
    if actual_keys != expected_keys:
        raise RCAOutputValidationError(
            "Hypothesis keys are missing, duplicated, or out of order."
        )

    # Validate hypothesis-to-evidence relationships.
    for proposal in proposals:
        links = get_typed_list(proposal, HypothesisEvidenceProposal)
        seen_evidence_ids: set[str] = set()
        for link in links:
            evidence_id = _value(
                getattr(link, "evidence_item_id", None)
            )
            relationship = _value(
                getattr(link, "relationship_type", None)
            )
            if evidence_id in seen_evidence_ids:
                raise RCAOutputValidationError(
                    "A hypothesis contains a duplicate evidence link."
                )
            if evidence_id is not None:
                seen_evidence_ids.add(evidence_id)
            validate_evidence_reference(
                evidence_id,
                evidence_by_id,
                purpose=relationship or "contextual",
            )

    # Every generated hypothesis must have exactly one detailed analysis.
    analyses = get_typed_list(details, HypothesisAnalysisProposal)
    analysis_keys = [
        _value(getattr(analysis, "hypothesis_key", None))
        for analysis in analyses
    ]
    if len(analysis_keys) != len(set(analysis_keys)):
        raise RCAOutputValidationError(
            "A hypothesis has more than one detailed analysis."
        )
    if set(analysis_keys) != set(expected_keys):
        raise RCAOutputValidationError(
            "Every generated hypothesis must have exactly one analysis."
        )

    # Validate source-supported 5-Whys answers.
    for analysis in analyses:
        steps = get_typed_list(analysis, WhyStepProposal)
        for step in steps:
            basis = _value(getattr(step, "answer_basis", None))
            evidence_id = _value(
                getattr(step, "evidence_item_id", None)
            )
            if basis == "source_supported":
                validate_evidence_reference(
                    evidence_id,
                    evidence_by_id,
                    purpose="source_supported",
                )
            elif evidence_id is not None:
                raise RCAOutputValidationError(
                    "Hypothesis-based or unknown 5-Whys answers "
                    "must not cite evidence IDs."
                )

    # Validate optional hypothesis references on evidence gaps.
    gaps = get_typed_list(details, EvidenceGapProposal)
    for gap in gaps:
        hypothesis_key = _value(
            getattr(gap, "hypothesis_key", None)
        )
        if (
            hypothesis_key is not None
            and hypothesis_key not in expected_keys
        ):
            raise RCAOutputValidationError(
                "An evidence gap references an unknown hypothesis key."
            )

    return {}
