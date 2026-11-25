"""LangGraph workflow for CAPA generation and adversarial stress testing."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.prompts.capa import (
    build_capa_generation_messages,
    build_capa_stress_test_messages,
)
from app.schemas.capa import (
    CAPA_GENERATION_JSON_SCHEMA,
    CAPAGenerationOutput,
)
from app.services.exceptions import RCAOutputValidationError
from app.services.groq_service import generate_structured_response


class CAPAState(TypedDict, total=False):
    """State passed between CAPA LangGraph nodes."""

    investigation_id: str
    investigation_summary: str
    rca_summary: str | None
    hypotheses_context: list[dict[str, Any]]
    draft_capa: dict[str, Any]
    final_capa: dict[str, Any]
    warnings: list[str]


def generate_capa_node(state: CAPAState) -> dict:
    """Generate initial CAPA proposals from hypotheses and 5-Whys."""
    hypotheses_context = state.get("hypotheses_context", [])
    if not hypotheses_context:
        raise RCAOutputValidationError(
            "Cannot generate CAPAs without RCA hypotheses."
        )

    messages = build_capa_generation_messages(
        investigation_summary=state.get("investigation_summary", ""),
        hypotheses_context=hypotheses_context,
        rca_summary=state.get("rca_summary"),
    )
    raw = generate_structured_response(
        messages=messages,
        schema_name="capa_generation",
        json_schema=CAPA_GENERATION_JSON_SCHEMA,
    )
    try:
        parsed = CAPAGenerationOutput.model_validate(raw)
    except Exception as exc:
        raise RCAOutputValidationError(
            "The model returned an invalid CAPA generation output."
        ) from exc

    return {
        "draft_capa": parsed.model_dump(mode="json"),
        "warnings": list(parsed.warnings),
    }


def stress_test_capa_node(state: CAPAState) -> dict:
    """Stress-test draft CAPAs for measurability, residual risk, and blind spots."""
    draft_capa = state.get("draft_capa")
    if not draft_capa:
        raise RCAOutputValidationError("Draft CAPA output is missing.")

    valid_keys = {
        h["hypothesis_key"] for h in state.get("hypotheses_context", [])
    }

    messages = build_capa_stress_test_messages(
        hypotheses_context=state.get("hypotheses_context", []),
        draft_capa=draft_capa,
    )
    raw = generate_structured_response(
        messages=messages,
        schema_name="capa_stress_test",
        json_schema=CAPA_GENERATION_JSON_SCHEMA,
    )
    try:
        parsed = CAPAGenerationOutput.model_validate(raw)
    except Exception as exc:
        raise RCAOutputValidationError(
            "The model returned an invalid CAPA stress-test output."
        ) from exc

    for rec in parsed.recommendations:
        if rec.hypothesis_key not in valid_keys:
            raise RCAOutputValidationError(
                f"CAPA references unknown hypothesis key: {rec.hypothesis_key}"
            )

    existing_warnings = list(state.get("warnings", []))
    combined_warnings = list(dict.fromkeys(existing_warnings + list(parsed.warnings)))

    return {
        "final_capa": parsed.model_dump(mode="json"),
        "warnings": combined_warnings,
    }


def build_capa_graph():
    """Build the two-step CAPA generation + adversarial stress-test graph."""
    workflow = StateGraph(CAPAState)
    workflow.add_node("generate_capa", generate_capa_node)
    workflow.add_node("stress_test_capa", stress_test_capa_node)

    workflow.add_edge(START, "generate_capa")
    workflow.add_edge("generate_capa", "stress_test_capa")
    workflow.add_edge("stress_test_capa", END)

    return workflow.compile()
