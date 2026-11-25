from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EvidenceRead(BaseModel):
    """Public evidence record representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    source_document_id: UUID
    evidence_kind: str
    content: str
    page_number: int | None
    source_start_char: int | None
    source_end_char: int | None
    field_name: str | None
    extracted_value: str | None
    review_status: str
    created_at: datetime


class EvidenceListResponse(BaseModel):
    """Paginated evidence response."""

    items: list[EvidenceRead]
    total: int
    limit: int
    offset: int
