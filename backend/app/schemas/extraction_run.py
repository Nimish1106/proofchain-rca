from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtractedFactResult(BaseModel):
    """A source-validated, persisted extraction."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_document_id: UUID
    field_name: str
    extracted_value: str
    content: str
    page_number: int
    source_start_char: int
    source_end_char: int
    review_status: str


class RejectedFactResult(BaseModel):
    """An AI suggestion rejected by source validation."""

    field_name: str
    extracted_value: str
    source_quote: str
    page_number: int
    reason: str


class ConflictCandidate(BaseModel):
    """One source value involved in a conflict."""

    value: str
    source_document_id: UUID
    original_filename: str
    page_number: int
    source_quote: str


class FieldConflict(BaseModel):
    """Multiple conflicting values for one field."""

    field_name: str
    status: Literal["requires_human_resolution"]
    candidates: list[ConflictCandidate]


class ExtractionRunResponse(BaseModel):
    """Complete response from a LangGraph extraction run."""

    investigation_id: UUID
    status: Literal[
        "completed",
        "no_extractable_text",
    ]
    summaries: list[str]
    extracted_facts: list[ExtractedFactResult]
    validated_fact_count: int
    new_facts_count: int
    duplicate_facts_count: int
    rejected_facts: list[RejectedFactResult]
    field_conflicts: list[FieldConflict]
    warnings: list[str]
