from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.rca_analysis import (
    HypothesisAnalysisProposal,
    HypothesisGenerationOutput,
    HypothesisProposal,
    RCAAnalysisDetailsOutput,
    WhyStepProposal,
)


def test_valid_hypothesis_proposal():
    result = HypothesisProposal(
        title="Potential equipment cleaning failure",
        description=(
            "Residual material may have contributed "
            "to the observed contamination."
        ),
        causal_mechanism="Possible equipment residue transfer.",
        evidence_links=[],
    )
    assert result.title.startswith("Potential")


def test_hypothesis_can_have_no_direct_evidence():
    result = HypothesisGenerationOutput(
        summary="Insufficient evidence for direct causal support.",
        hypotheses=[
            {
                "title": "Potential filtration failure",
                "description": "An unverified possibility.",
                "causal_mechanism": None,
                "evidence_links": [],
            }
        ],
        warnings=["Filter integrity report unavailable."],
    )
    assert len(result.hypotheses) == 1
    assert result.hypotheses[0].evidence_links == []


def test_hypothesis_generation_allows_zero_hypotheses():
    result = HypothesisGenerationOutput(
        summary="Available information is insufficient.",
        hypotheses=[],
        warnings=["Additional investigation is required."],
    )
    assert result.hypotheses == []


def test_source_supported_why_requires_evidence():
    with pytest.raises(ValidationError):
        WhyStepProposal(
            step_number=1,
            question="Why was contamination detected?",
            answer="Foreign matter was detected.",
            answer_basis="source_supported",
            evidence_item_id=None,
        )


def test_hypothesis_basis_cannot_claim_source_reference():
    with pytest.raises(ValidationError):
        WhyStepProposal(
            step_number=1,
            question="Why may contamination have occurred?",
            answer="Possible cleaning failure.",
            answer_basis="hypothesis",
            evidence_item_id=uuid4(),
        )


def test_valid_unknown_why_step():
    step = WhyStepProposal(
        step_number=1,
        question="What caused the foreign matter?",
        answer=None,
        answer_basis="unknown",
        evidence_item_id=None,
    )
    assert step.answer_basis == "unknown"


def test_duplicate_why_step_numbers_rejected():
    with pytest.raises(ValidationError):
        HypothesisAnalysisProposal(
            hypothesis_key="H1",
            why_steps=[
                {
                    "step_number": 1,
                    "question": "Why 1?",
                    "answer": "Answer 1",
                    "answer_basis": "hypothesis",
                    "evidence_item_id": None,
                },
                {
                    "step_number": 1,
                    "question": "Why 2?",
                    "answer": "Answer 2",
                    "answer_basis": "hypothesis",
                    "evidence_item_id": None,
                },
            ],
            evidence_gaps=[],
        )


def test_non_sequential_why_steps_rejected():
    with pytest.raises(ValidationError):
        HypothesisAnalysisProposal(
            hypothesis_key="H1",
            why_steps=[
                {
                    "step_number": 2,
                    "question": "Why 2?",
                    "answer": "Possible answer.",
                    "answer_basis": "hypothesis",
                    "evidence_item_id": None,
                },
                {
                    "step_number": 1,
                    "question": "Why 1?",
                    "answer": "Possible answer.",
                    "answer_basis": "hypothesis",
                    "evidence_item_id": None,
                },
            ],
            evidence_gaps=[],
        )


def test_unknown_properties_rejected():
    with pytest.raises(ValidationError):
        HypothesisGenerationOutput(
            summary="Test",
            hypotheses=[],
            warnings=[],
            confidence=0.99,
        )


def test_invalid_hypothesis_key_rejected():
    with pytest.raises(ValidationError):
        HypothesisAnalysisProposal(
            hypothesis_key="H4",
            why_steps=[
                {
                    "step_number": 1,
                    "question": "Why?",
                    "answer": None,
                    "answer_basis": "unknown",
                    "evidence_item_id": None,
                }
            ],
            evidence_gaps=[],
        )


def test_complete_rca_details_schema():
    result = RCAAnalysisDetailsOutput(
        summary="Investigation requires more information.",
        analyses=[
            {
                "hypothesis_key": "H1",
                "why_steps": [
                    {
                        "step_number": 1,
                        "question": "Why was the issue observed?",
                        "answer": None,
                        "answer_basis": "unknown",
                        "evidence_item_id": None,
                    }
                ],
                "evidence_gaps": [],
            }
        ],
        global_gaps=[],
        warnings=[],
    )
    assert result.analyses[0].hypothesis_key == "H1"
