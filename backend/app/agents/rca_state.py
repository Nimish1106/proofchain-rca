from typing import Any, TypedDict

EvidencePayload = dict[str, Any]


class RCAState(TypedDict, total=False):
    """State passed between RCA LangGraph nodes."""

    investigation_id: str
    run_id: str
    model_name: str
    evidence_items: list[EvidencePayload]
    input_fingerprint: str

    # Output from the first reasoning stage.
    hypothesis_generation: dict[str, Any]

    # Hypotheses after deterministic H1/H2/H3 key assignment.
    hypotheses: list[dict[str, Any]]

    # Output from the detailed 5-Whys and evidence-gap stage.
    analysis_details: dict[str, Any]
