"""Text and email ingestion schemas."""

from pydantic import BaseModel, ConfigDict, Field


class TextIngestionRequest(BaseModel):
    """Ingest plain text as a source document."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=255,
    )
    content: str = Field(
        min_length=1,
        max_length=500_000,
    )


class EmailIngestionRequest(BaseModel):
    """Ingest an email as a source document."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(
        min_length=1,
        max_length=500,
    )
    sender: str = Field(
        min_length=1,
        max_length=255,
    )
    date: str | None = None
    body: str = Field(
        min_length=1,
        max_length=500_000,
    )
