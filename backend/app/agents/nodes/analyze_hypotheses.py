from app.agents.prompts.rca import (
    build_analysis_details_messages,
    compact_evidence_for_prompt,
    compact_hypotheses_for_analysis,
)
from app.agents.rca_state import RCAState
from app.schemas.rca_analysis import (
    RCA_ANALYSIS_DETAILS_JSON_SCHEMA,
    RCAAnalysisDetailsOutput,
)
from app.services.exceptions import RCAOutputValidationError
from app.services.groq_service import generate_structured_response


def analyze_hypotheses(state: RCAState) -> dict:
    """Generate 5-Whys analysis and evidence gaps for proposed hypotheses."""
    evidence_items = state.get("evidence_items", [])
    hypotheses = state.get("hypotheses", [])
    if not evidence_items:
        raise RCAOutputValidationError(
            "RCA analysis cannot run without evidence."
        )

    messages = build_analysis_details_messages(
        evidence_items=compact_evidence_for_prompt(evidence_items),
        hypotheses=compact_hypotheses_for_analysis(hypotheses),
    )
    raw_output = generate_structured_response(
        messages=messages,
        schema_name="rca_analysis_details",
        json_schema=RCA_ANALYSIS_DETAILS_JSON_SCHEMA,
    )

    try:
        parsed = RCAAnalysisDetailsOutput.model_validate(raw_output)
    except Exception as exc:
        raise RCAOutputValidationError(
            "The model returned an invalid RCA analysis result."
        ) from exc

    return {
        "analysis_details": parsed.model_dump(mode="json"),
    }
