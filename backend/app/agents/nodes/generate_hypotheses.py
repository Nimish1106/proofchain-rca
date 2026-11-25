from app.agents.nodes.rca_schema_utils import get_typed_list
from app.agents.prompts.rca import (
    build_hypothesis_messages,
    compact_evidence_for_prompt,
)
from app.agents.rca_state import RCAState
from app.schemas.rca_analysis import (
    HYPOTHESIS_GENERATION_JSON_SCHEMA,
    HypothesisGenerationOutput,
    HypothesisProposal,
)
from app.services.exceptions import RCAOutputValidationError
from app.services.groq_service import (
    generate_structured_response,
    get_configured_model,
)


def generate_hypotheses(state: RCAState) -> dict:
    """Generate and key up to three hypotheses from supplied evidence."""
    evidence_items = state.get("evidence_items", [])
    if not evidence_items:
        raise RCAOutputValidationError(
            "RCA cannot generate hypotheses without evidence."
        )

    model_name = get_configured_model()
    messages = build_hypothesis_messages(
        compact_evidence_for_prompt(evidence_items)
    )
    raw_output = generate_structured_response(
        messages=messages,
        schema_name="rca_hypothesis_generation",
        json_schema=HYPOTHESIS_GENERATION_JSON_SCHEMA,
    )

    try:
        parsed = HypothesisGenerationOutput.model_validate(raw_output)
        proposals = get_typed_list(parsed, HypothesisProposal)
    except Exception as exc:
        raise RCAOutputValidationError(
            "The model returned an invalid hypothesis-generation result."
        ) from exc

    if len(proposals) > 3:
        raise RCAOutputValidationError(
            "The model returned more than three hypotheses."
        )

    # Assign keys deterministically. The model does not control these keys.
    keyed_hypotheses: list[dict] = []
    for index, proposal in enumerate(proposals, start=1):
        hypothesis = proposal.model_dump(mode="json")
        hypothesis["hypothesis_key"] = f"H{index}"
        keyed_hypotheses.append(hypothesis)

    return {
        "model_name": model_name,
        "hypothesis_generation": parsed.model_dump(mode="json"),
        "hypotheses": keyed_hypotheses,
    }
