import pytest
from pydantic import BaseModel

from app.agents.nodes.analyze_hypotheses import analyze_hypotheses
from app.agents.nodes.generate_hypotheses import generate_hypotheses
from app.agents.nodes.rca_schema_utils import get_typed_list
from app.agents.nodes.validate_rca import validate_evidence_reference
from app.services.exceptions import RCAOutputValidationError


class SampleChild(BaseModel):
    value: str


class SampleContainer(BaseModel):
    children: list[SampleChild]


class OptionalSampleContainer(BaseModel):
    children: list[SampleChild] | None = None


class SampleContainerWithoutChildren(BaseModel):
    value: str


def test_get_typed_list_returns_matching_items():
    child = SampleChild(value="test")
    container = SampleContainer(children=[child])
    assert get_typed_list(container, SampleChild) == [child]


def test_get_typed_list_handles_optional_empty_list():
    container = OptionalSampleContainer(children=None)
    assert get_typed_list(container, SampleChild) == []


def test_get_typed_list_rejects_missing_list_field():
    container = SampleContainerWithoutChildren(value="test")
    with pytest.raises(ValueError, match="found 0"):
        get_typed_list(container, SampleChild)


def test_unknown_evidence_reference_is_rejected():
    with pytest.raises(
        RCAOutputValidationError,
        match="Unknown evidence reference",
    ):
        validate_evidence_reference(
            "unknown-id",
            {},
            purpose="supports",
        )


def test_missing_evidence_reference_is_rejected():
    with pytest.raises(
        RCAOutputValidationError,
        match="evidence reference is required",
    ):
        validate_evidence_reference(
            None,
            {},
            purpose="source_supported",
        )


def test_pending_extracted_fact_cannot_support_hypothesis():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "pending",
        }
    }
    with pytest.raises(
        RCAOutputValidationError,
        match="Pending extracted evidence",
    ):
        validate_evidence_reference(
            "evidence-001",
            evidence,
            purpose="supports",
        )


def test_pending_extracted_fact_cannot_contradict_hypothesis():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "pending",
        }
    }
    with pytest.raises(
        RCAOutputValidationError,
        match="Pending extracted evidence",
    ):
        validate_evidence_reference(
            "evidence-001",
            evidence,
            purpose="contradicts",
        )


def test_pending_extracted_fact_can_be_contextual():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "pending",
        }
    }
    result = validate_evidence_reference(
        "evidence-001",
        evidence,
        purpose="contextual",
    )
    assert result["evidence_id"] == "evidence-001"


def test_pending_extracted_fact_cannot_be_source_supported():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "pending",
        }
    }
    with pytest.raises(
        RCAOutputValidationError,
        match="Pending extracted evidence",
    ):
        validate_evidence_reference(
            "evidence-001",
            evidence,
            purpose="source_supported",
        )


def test_rejected_extracted_fact_cannot_be_cited():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "rejected",
        }
    }
    with pytest.raises(
        RCAOutputValidationError,
        match="Rejected extracted evidence",
    ):
        validate_evidence_reference(
            "evidence-001",
            evidence,
            purpose="contextual",
        )


def test_accepted_extracted_fact_can_support_hypothesis():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "extracted_fact",
            "review_status": "accepted",
        }
    }
    result = validate_evidence_reference(
        "evidence-001",
        evidence,
        purpose="supports",
    )
    assert result["evidence_id"] == "evidence-001"


def test_source_excerpt_can_support_hypothesis():
    evidence = {
        "evidence-001": {
            "evidence_id": "evidence-001",
            "evidence_kind": "source_excerpt",
            "review_status": None,
        }
    }
    result = validate_evidence_reference(
        "evidence-001",
        evidence,
        purpose="supports",
    )
    assert result["evidence_id"] == "evidence-001"


def test_hypothesis_node_rejects_empty_evidence():
    with pytest.raises(
        RCAOutputValidationError,
        match="without evidence",
    ):
        generate_hypotheses({"evidence_items": []})


def test_analysis_node_rejects_empty_evidence():
    with pytest.raises(
        RCAOutputValidationError,
        match="without evidence",
    ):
        analyze_hypotheses({"evidence_items": []})
