"""Response schemas for RCA API endpoints."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class HypothesisEvidenceLinkRead(BaseModel):
    """Public representation of a hypothesis-evidence relationship."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    evidence_item_id: UUID
    relationship_type: str
    rationale: str
    created_at: datetime


class WhyStepRead(BaseModel):
    """Public representation of a 5-Whys step."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hypothesis_id: UUID
    step_number: int
    question: str
    answer: str | None
    answer_basis: str
    evidence_item_id: UUID | None
    created_at: datetime
    updated_at: datetime


class EvidenceGapRead(BaseModel):
    """Public representation of an evidence gap."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    analysis_run_id: UUID
    hypothesis_id: UUID | None
    gap_type: str
    description: str
    recommended_question: str | None
    priority: str
    status: str
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HypothesisRead(BaseModel):
    """Public representation of an RCA hypothesis."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    analysis_run_id: UUID
    title: str
    description: str
    causal_mechanism: str | None
    status: str
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HypothesisDetailRead(HypothesisRead):
    """Hypothesis with nested evidence links, why steps, and gaps."""

    evidence_links: list[HypothesisEvidenceLinkRead]
    why_steps: list[WhyStepRead]
    evidence_gaps: list[EvidenceGapRead]


class RCARunSummaryRead(BaseModel):
    """Summary of one RCA analysis run."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    model_name: str
    input_fingerprint: str
    status: str
    summary: str | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None


class RCARunDetailRead(RCARunSummaryRead):
    """Full RCA run with hypotheses, evidence links, and gaps."""

    hypotheses: list[HypothesisDetailRead]
    global_gaps: list[EvidenceGapRead]


class RCARunListResponse(BaseModel):
    """Paginated list of RCA analysis runs."""

    items: list[RCARunSummaryRead]
    total: int


class HypothesisStatusUpdate(BaseModel):
    """Update the review status of a hypothesis."""

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "proposed",
        "under_review",
        "supported_by_records",
        "contradicted",
        "rejected",
        "confirmed_by_investigator",
    ]
    review_note: str | None = None


class EvidenceReviewUpdate(BaseModel):
    """Update the review status of an evidence item."""

    model_config = ConfigDict(extra="forbid")

    review_status: Literal[
        "pending",
        "accepted",
        "rejected",
    ]
    review_note: str | None = None
    apply_to_investigation: bool = False


class WhyStepUpdate(BaseModel):
    """Edit a 5-Whys step."""

    model_config = ConfigDict(extra="forbid")

    question: str | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def validate_updates(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if self.question is not None and not self.question.strip():
            raise ValueError("Question cannot be empty.")
        return self


class EvidenceGapUpdate(BaseModel):
    """Resolve or waive an evidence gap."""

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "open",
        "addressed",
        "waived",
    ]
    resolution_note: str | None = None
