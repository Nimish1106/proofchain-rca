import pytest

from app.agents import rca_graph
from app.services.exceptions import RCAOutputValidationError

EVIDENCE_1_ID = "11111111-1111-1111-1111-111111111111"
EVIDENCE_2_ID = "22222222-2222-2222-2222-222222222222"
DOCUMENT_1_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
UNKNOWN_EVIDENCE_ID = "99999999-9999-9999-9999-999999999999"


def sample_evidence_context():
    """Representative evidence payload returned by the RCA context layer."""
    return [
        {
            "evidence_id": EVIDENCE_1_ID,
            "source_document_id": DOCUMENT_1_ID,
            "source_filename": "batch-investigation.pdf",
            "evidence_kind": "source_excerpt",
            "content": (
                "The batch manufacturing record shows a reactor "
                "temperature reading of 82 C at 14:30."
            ),
            "page_number": 3,
            "field_name": None,
            "extracted_value": None,
            "review_status": None,
        },
        {
            "evidence_id": EVIDENCE_2_ID,
            "source_document_id": DOCUMENT_1_ID,
            "source_filename": "batch-investigation.pdf",
            "evidence_kind": "source_excerpt",
            "content": (
                "The approved operating range for this process stage "
                "is 70 C to 75 C."
            ),
            "page_number": 2,
            "field_name": None,
            "extracted_value": None,
            "review_status": None,
        },
    ]


def sample_hypothesis_response(evidence_id=EVIDENCE_1_ID):
    return {
        "summary": (
            "The recorded temperature is above the documented "
            "operating range."
        ),
        "hypotheses": [
            {
                "title": "Potential reactor temperature control deviation",
                "description": (
                    "The reactor temperature may have exceeded the "
                    "approved operating range during processing."
                ),
                "causal_mechanism": (
                    "A temperature control issue may have allowed "
                    "the reactor temperature to rise above its range."
                ),
                "evidence_links": [
                    {
                        "evidence_item_id": evidence_id,
                        "relationship_type": "supports",
                        "rationale": (
                            "The source records a temperature reading "
                            "of 82 C."
                        ),
                    }
                ],
            }
        ],
        "warnings": [
            "The available records do not establish the cause "
            "of the temperature excursion."
        ],
    }


def sample_analysis_response(evidence_id=EVIDENCE_1_ID):
    return {
        "summary": (
            "The available record identifies a temperature reading "
            "above the documented operating range."
        ),
        "analyses": [
            {
                "hypothesis_key": "H1",
                "why_steps": [
                    {
                        "step_number": 1,
                        "question": (
                            "Why is a temperature deviation suspected?"
                        ),
                        "answer": (
                            "The batch record documents a reading "
                            "of 82 C."
                        ),
                        "answer_basis": "source_supported",
                        "evidence_item_id": evidence_id,
                    },
                    {
                        "step_number": 2,
                        "question": (
                            "Why did the temperature reach 82 C?"
                        ),
                        "answer": (
                            "A control-system issue is one possibility, "
                            "but the available evidence does not establish it."
                        ),
                        "answer_basis": "hypothesis",
                        "evidence_item_id": None,
                    },
                    {
                        "step_number": 3,
                        "question": (
                            "What record would establish the control-system "
                            "condition?"
                        ),
                        "answer": (
                            "The available evidence does not establish "
                            "the control-system condition."
                        ),
                        "answer_basis": "unknown",
                        "evidence_item_id": None,
                    },
                ],
                "evidence_gaps": [
                    {
                        "gap_type": "missing_record",
                        "description": (
                            "The temperature controller alarm history "
                            "has not been supplied."
                        ),
                        "recommended_question": (
                            "Can the controller alarm history for this "
                            "batch be obtained?"
                        ),
                        "priority": "high",
                    }
                ],
            }
        ],
        "global_gaps": [],
        "warnings": [
            "The proposed mechanism requires further investigation."
        ],
    }


def configure_mocked_groq(monkeypatch, hypothesis_response, analysis_response):
    calls = []

    def fake_generate_structured_response(
        *,
        messages,
        schema_name,
        json_schema,
    ):
        calls.append(
            {
                "schema_name": schema_name,
                "messages": messages,
                "json_schema": json_schema,
            }
        )
        if schema_name == "rca_hypothesis_generation":
            return hypothesis_response
        if schema_name == "rca_analysis_details":
            return analysis_response
        raise AssertionError(
            f"Unexpected Groq schema name: {schema_name}"
        )

    monkeypatch.setattr(
        "app.agents.nodes.generate_hypotheses.generate_structured_response",
        fake_generate_structured_response,
    )
    monkeypatch.setattr(
        "app.agents.nodes.generate_hypotheses.get_configured_model",
        lambda: "test-model",
    )
    monkeypatch.setattr(
        "app.agents.nodes.analyze_hypotheses.generate_structured_response",
        fake_generate_structured_response,
    )
    return calls


def initial_state():
    return {
        "investigation_id": "investigation-001",
        "run_id": "run-001",
        "model_name": "test-model",
        "input_fingerprint": "test-fingerprint",
        "evidence_items": sample_evidence_context(),
    }


def test_rca_graph_completes_with_valid_mocked_groq_responses(monkeypatch):
    calls = configure_mocked_groq(
        monkeypatch,
        sample_hypothesis_response(),
        sample_analysis_response(),
    )

    graph = rca_graph.build_rca_graph()
    result = graph.invoke(initial_state())

    assert len(calls) == 2
    assert calls[0]["schema_name"] == "rca_hypothesis_generation"
    assert calls[1]["schema_name"] == "rca_analysis_details"
    assert result["model_name"] == "test-model"
    assert len(result["hypotheses"]) == 1
    assert result["hypotheses"][0]["hypothesis_key"] == "H1"
    assert result["analysis_details"]["analyses"][0]["hypothesis_key"] == "H1"
    assert (
        result["analysis_details"]["analyses"][0]["why_steps"][0][
            "answer_basis"
        ]
        == "source_supported"
    )
    assert (
        result["analysis_details"]["analyses"][0]["evidence_gaps"][0][
            "gap_type"
        ]
        == "missing_record"
    )


def test_rca_graph_rejects_unknown_evidence_id(monkeypatch):
    calls = configure_mocked_groq(
        monkeypatch,
        sample_hypothesis_response(evidence_id=UNKNOWN_EVIDENCE_ID),
        sample_analysis_response(),
    )

    graph = rca_graph.build_rca_graph()

    with pytest.raises(
        RCAOutputValidationError,
        match="Unknown evidence reference",
    ):
        graph.invoke(initial_state())

    # Both model calls complete, but validation rejects their output.
    assert len(calls) == 2


def test_rca_graph_rejects_pending_fact_as_source_supported(monkeypatch):
    evidence = sample_evidence_context()
    evidence[0]["evidence_kind"] = "extracted_fact"
    evidence[0]["review_status"] = "pending"

    calls = configure_mocked_groq(
        monkeypatch,
        sample_hypothesis_response(),
        sample_analysis_response(),
    )

    state = initial_state()
    state["evidence_items"] = evidence

    graph = rca_graph.build_rca_graph()

    with pytest.raises(
        RCAOutputValidationError,
        match="Pending extracted evidence",
    ):
        graph.invoke(state)

    assert len(calls) == 2
