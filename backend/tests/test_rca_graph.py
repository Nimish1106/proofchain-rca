import pytest

from app.agents import rca_graph
from app.services.exceptions import RCAOutputValidationError


def sample_initial_state():
    return {
        "investigation_id": "investigation-001",
        "run_id": "run-001",
        "model_name": "test-model",
        "input_fingerprint": "fingerprint-001",
        "evidence_items": [
            {
                "evidence_id": "evidence-001",
                "source_document_id": "document-001",
                "evidence_kind": "source_excerpt",
                "content": "Recorded temperature was 82 C.",
                "page_number": 1,
                "field_name": None,
                "extracted_value": None,
                "review_status": None,
            }
        ],
    }


def test_rca_graph_executes_nodes_in_correct_order(monkeypatch):
    execution_order = []

    def fake_generate(state):
        execution_order.append("generate_hypotheses")
        return {
            "model_name": "test-model",
            "hypothesis_generation": {"hypotheses": []},
            "hypotheses": [],
        }

    def fake_analyze(state):
        execution_order.append("analyze_hypotheses")
        assert state["hypotheses"] == []
        return {
            "analysis_details": {
                "hypothesis_analyses": [],
                "evidence_gaps": [],
            }
        }

    def fake_validate(state):
        execution_order.append("validate_rca")
        assert state["hypothesis_generation"] is not None
        assert state["analysis_details"] is not None
        return {}

    monkeypatch.setattr(
        rca_graph,
        "generate_hypotheses",
        fake_generate,
    )
    monkeypatch.setattr(
        rca_graph,
        "analyze_hypotheses",
        fake_analyze,
    )
    monkeypatch.setattr(
        rca_graph,
        "validate_rca",
        fake_validate,
    )

    graph = rca_graph.build_rca_graph()
    result = graph.invoke(sample_initial_state())

    assert execution_order == [
        "generate_hypotheses",
        "analyze_hypotheses",
        "validate_rca",
    ]
    assert result["hypotheses"] == []
    assert result["analysis_details"]["evidence_gaps"] == []


def test_rca_graph_propagates_validation_failure(monkeypatch):
    def fake_generate(state):
        return {
            "hypothesis_generation": {"hypotheses": []},
            "hypotheses": [],
        }

    def fake_analyze(state):
        return {
            "analysis_details": {
                "hypothesis_analyses": [],
                "evidence_gaps": [],
            }
        }

    def fake_validate(state):
        raise RCAOutputValidationError(
            "Test validation failure."
        )

    monkeypatch.setattr(
        rca_graph,
        "generate_hypotheses",
        fake_generate,
    )
    monkeypatch.setattr(
        rca_graph,
        "analyze_hypotheses",
        fake_analyze,
    )
    monkeypatch.setattr(
        rca_graph,
        "validate_rca",
        fake_validate,
    )

    graph = rca_graph.build_rca_graph()

    with pytest.raises(
        RCAOutputValidationError,
        match="Test validation failure",
    ):
        graph.invoke(sample_initial_state())


def test_rca_graph_does_not_require_database_session():
    graph = rca_graph.build_rca_graph()
    assert graph is not None
    assert callable(graph.invoke)


def test_rca_graph_does_not_mutate_initial_input(monkeypatch):
    initial_state = sample_initial_state()
    original_evidence = [
        dict(item) for item in initial_state["evidence_items"]
    ]

    monkeypatch.setattr(
        rca_graph,
        "generate_hypotheses",
        lambda state: {
            "hypothesis_generation": {"hypotheses": []},
            "hypotheses": [],
        },
    )
    monkeypatch.setattr(
        rca_graph,
        "analyze_hypotheses",
        lambda state: {
            "analysis_details": {
                "hypothesis_analyses": [],
                "evidence_gaps": [],
            }
        },
    )
    monkeypatch.setattr(
        rca_graph,
        "validate_rca",
        lambda state: {},
    )

    graph = rca_graph.build_rca_graph()
    graph.invoke(initial_state)

    assert initial_state["evidence_items"] == original_evidence
