from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceDocumentRead(BaseModel):
    """Safe public representation of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    document_type: str
    original_filename: str
    content_type: str
    file_size_bytes: int
    sha256: str
    page_count: int
    extraction_status: str
    created_at: datetime


class SourceDocumentListResponse(BaseModel):
    """Paginated source document response."""

    items: list[SourceDocumentRead]
    total: int
    limit: int
    offset: int


class DocumentUploadResponse(BaseModel):
    """Result of uploading and processing a document."""

    document: SourceDocumentRead
    evidence_items_created: int
    pages_without_text: list[int] = Field(
        default_factory=list
    )
    extracted_text_characters: int
