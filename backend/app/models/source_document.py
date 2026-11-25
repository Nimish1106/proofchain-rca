import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SourceDocument(Base):
    """
    Metadata for a document associated with an investigation.

    Original file contents are stored in private local storage.
    This table stores metadata and the internal storage key.
    """

    __tablename__ = "source_documents"

    __table_args__ = (
        CheckConstraint(
            "file_size_bytes > 0",
            name="valid_file_size",
        ),
        CheckConstraint(
            "page_count >= 0",
            name="valid_page_count",
        ),
        CheckConstraint(
            """
            extraction_status IN (
                'text_extracted',
                'partial_text',
                'needs_ocr'
            )
            """,
            name="valid_extraction_status",
        ),
        UniqueConstraint(
            "id",
            "investigation_id",
            name="uq_source_documents_id_investigation",
        ),
        Index(
            "ix_source_documents_investigation_created_at",
            "investigation_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "investigations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pdf",
        server_default="pdf",
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # Internal relative storage key.
    # Never expose this as a public filesystem path.
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    page_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    extraction_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"SourceDocument("
            f"id={self.id}, "
            f"filename={self.original_filename!r}"
            f")"
        )
