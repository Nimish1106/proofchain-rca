import copy
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.models.evidence_gap import EvidenceGap
from app.models.evidence_item import EvidenceItem
from app.models.hypothesis_evidence import HypothesisEvidence
from app.models.investigation import Investigation
from app.models.rca_analysis_run import RCAAnalysisRun
from app.models.rca_hypothesis import RCAHypothesis
from app.models.source_document import SourceDocument
from app.models.why_step import WhyStep
from app.services import rca_service


@pytest.fixture
def rca_source_records(db_session):
    """Create an investigation, source document and source evidence."""
    investigation = Investigation(
        id=uuid4(),
        title="Synthetic RCA persistence test",
        status="draft",
    )
    db_session.add(investigation)
    db_session.flush()

    document_id = uuid4()
    document = SourceDocument(
        id=document_id,
        investigation_id=investigation.id,
        original_filename="synthetic-deviation.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256="a" * 64,
        storage_key=f"test/{document_id}.pdf",
        page_count=1,
        extraction_status="text_extracted",
    )
    db_session.add(document)
    db_session.flush()

    evidence = EvidenceItem(
        id=uuid4(),
        investigation_id=investigation.id,
        source_document_id=document.id,
        evidence_kind="source_excerpt",
        content=(
            "The drying stage was stopped before "
            "the validated hold time."
        ),
        page_number=1,
        review_status="accepted",
    )
    db_session.add(evidence)
    db_session.commit()

    return investigation, document, evidence


def make_graph_output(
    evidence_id,
    *,
    relationship_type="supports",
):
    """Create deterministic, schema-compatible RCA graph output."""
    evidence_id = str(evidence_id)
    return {
        "hypotheses": [
            {
                "hypothesis_key": "H1",
                "title": "Insufficient drying time",
                "description": (
                    "The drying operation may have ended "
                    "before the required hold time."
                ),
                "causal_mechanism": (
                    "An abbreviated drying period may "
                    "leave residual moisture."
                ),
                "evidence_links": [
                    {
                        "evidence_item_id": evidence_id,
                        "relationship_type": relationship_type,
                        "rationale": (
                            "The source excerpt records an early stop."
                        ),
                    }
                ],
            }
        ],
        "analysis_details": {
            "summary": (
                "The investigation requires further verification."
            ),
            "analyses": [
                {
                    "hypothesis_key": "H1",
                    "why_steps": [
                        {
                            "step_number": 1,
                            "question": (
                                "Why may residual moisture remain?"
                            ),
                            "answer": (
                                "The drying stage may have ended early."
                            ),
                            "answer_basis": "source_supported",
                            "evidence_item_id": evidence_id,
                        },
                        {
                            "step_number": 2,
                            "question": (
                                "Why did the stage end early?"
                            ),
                            "answer": (
                                "The stop condition needs investigation."
                            ),
                            "answer_basis": "hypothesis",
                            "evidence_item_id": None,
                        },
                    ],
                    "evidence_gaps": [
                        {
                            "gap_type": "missing_record",
                            "description": (
                                "The complete equipment event log "
                                "is not available."
                            ),
                            "recommended_question": (
                                "Can the equipment event log be retrieved?"
                            ),
                            "priority": "high",
                        }
                    ],
                }
            ],
            "global_gaps": [
                {
                    "gap_type": "insufficient_detail",
                    "description": (
                        "The investigation record does not "
                        "identify the operator."
                    ),
                    "recommended_question": (
                        "Who operated the equipment during the event?"
                    ),
                    "priority": "medium",
                }
            ],
            "warnings": [
                "The proposed cause is not confirmed."
            ],
        },
        "hypothesis_generation": {
            "warnings": [
                "AI-generated hypothesis requires investigator review."
            ],
        },
    }


class SuccessfulGraph:
    """Graph substitute returning deterministic output."""

    def __init__(
        self,
        output,
        expected_investigation_id,
        expected_evidence_id,
    ):
        self.output = output
        self.expected_investigation_id = str(
            expected_investigation_id
        )
        self.expected_evidence_id = str(expected_evidence_id)

    def invoke(self, state):
        assert (
            state["investigation_id"]
            == self.expected_investigation_id
        )
        assert state["evidence_items"]
        assert (
            state["evidence_items"][0]["evidence_id"]
            == self.expected_evidence_id
        )
        assert len(state["input_fingerprint"]) == 64
        return copy.deepcopy(self.output)


class FailingGraph:
    """Graph substitute simulating an AI execution failure."""

    def invoke(self, state):
        raise RuntimeError("simulated graph failure")


def configure_service(monkeypatch, graph):
    """Replace external AI execution with a deterministic test graph."""
    monkeypatch.setattr(
        rca_service,
        "get_configured_model",
        lambda: "test-model",
    )
    monkeypatch.setattr(
        rca_service,
        "build_rca_graph",
        lambda: graph,
    )


def make_settings():
    """Prevent tests from reading the project-root .env file."""
    return Settings(
        _env_file=None,
        app_env="test",
    )


def test_run_rca_analysis_persists_all_children_and_keeps_hypothesis_proposed(
    db_session,
    monkeypatch,
    rca_source_records,
):
    investigation, _, evidence = rca_source_records
    graph_output = make_graph_output(evidence.id)
    graph = SuccessfulGraph(
        graph_output,
        investigation.id,
        evidence.id,
    )
    configure_service(monkeypatch, graph)

    result = rca_service.run_rca_analysis(
        db=db_session,
        investigation_id=investigation.id,
        settings=make_settings(),
    )

    run = db_session.get(
        RCAAnalysisRun,
        UUID(result["analysis_run_id"]),
    )
    assert run is not None
    assert run.status == "completed"
    assert run.model_name == "test-model"
    assert run.input_fingerprint == result["input_fingerprint"]
    assert run.summary == graph_output["analysis_details"]["summary"]
    assert run.completed_at is not None

    # Verify persisted hypothesis.
    hypotheses = db_session.scalars(
        select(RCAHypothesis).where(
            RCAHypothesis.analysis_run_id == run.id
        )
    ).all()
    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis.status == "proposed"
    assert hypothesis.title == "Insufficient drying time"

    # Verify hypothesis-evidence relationship.
    links = db_session.scalars(
        select(HypothesisEvidence).where(
            HypothesisEvidence.hypothesis_id == hypothesis.id
        )
    ).all()
    assert len(links) == 1
    assert links[0].evidence_item_id == evidence.id
    assert links[0].relationship_type == "supports"

    # Verify 5-Whys persistence.
    why_steps = db_session.scalars(
        select(WhyStep).where(
            WhyStep.hypothesis_id == hypothesis.id
        )
    ).all()
    assert len(why_steps) == 2

    source_supported_step = next(
        step
        for step in why_steps
        if step.answer_basis == "source_supported"
    )
    hypothesis_step = next(
        step
        for step in why_steps
        if step.answer_basis == "hypothesis"
    )
    assert source_supported_step.evidence_item_id == evidence.id
    assert hypothesis_step.evidence_item_id is None

    # Verify evidence gaps.
    gaps = db_session.scalars(
        select(EvidenceGap).where(
            EvidenceGap.analysis_run_id == run.id
        )
    ).all()
    assert len(gaps) == 2

    linked_gap = next(
        gap for gap in gaps if gap.hypothesis_id is not None
    )
    global_gap = next(
        gap for gap in gaps if gap.hypothesis_id is None
    )
    assert linked_gap.hypothesis_id == hypothesis.id
    assert linked_gap.status == "open"
    assert global_gap.status == "open"

    assert result["warnings"] == [
        "AI-generated hypothesis requires investigator review.",
        "The proposed cause is not confirmed.",
    ]


def test_graph_failure_marks_run_failed_without_child_records(
    db_session,
    monkeypatch,
    rca_source_records,
):
    investigation, _, _ = rca_source_records
    configure_service(monkeypatch, FailingGraph())

    with pytest.raises(
        RuntimeError,
        match="simulated graph failure",
    ):
        rca_service.run_rca_analysis(
            db=db_session,
            investigation_id=investigation.id,
            settings=make_settings(),
        )

    run = db_session.scalar(select(RCAAnalysisRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "RuntimeError"
    assert run.completed_at is not None

    # A failed AI execution must not leave partial child records.
    assert (
        db_session.scalar(
            select(func.count()).select_from(RCAHypothesis)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(HypothesisEvidence)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(WhyStep)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(EvidenceGap)
        )
        == 0
    )


def test_child_persistence_failure_rolls_back_all_children_and_marks_run_failed(
    db_session,
    monkeypatch,
    rca_source_records,
):
    investigation, _, evidence = rca_source_records

    # Deliberately violate the database relationship-type CHECK constraint.
    graph_output = make_graph_output(
        evidence.id,
        relationship_type="not-a-valid-relationship",
    )
    graph = SuccessfulGraph(
        graph_output,
        investigation.id,
        evidence.id,
    )
    configure_service(monkeypatch, graph)

    with pytest.raises(IntegrityError):
        rca_service.run_rca_analysis(
            db=db_session,
            investigation_id=investigation.id,
            settings=make_settings(),
        )

    run = db_session.scalar(select(RCAAnalysisRun))
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "IntegrityError"
    assert run.completed_at is not None

    # The analysis run is retained for audit.
    # All child records from the failed transaction must be rolled back.
    assert (
        db_session.scalar(
            select(func.count()).select_from(RCAHypothesis)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(HypothesisEvidence)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(WhyStep)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(EvidenceGap)
        )
        == 0
    )
