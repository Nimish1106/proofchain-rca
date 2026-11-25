import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EvidenceItem(Base):
    """
    Stores original source excerpts and AI-extracted facts.

    AI-generated facts remain pending human review.
    """

    __tablename__ = "evidence_items"

    __table_args__ = (
        CheckConstraint(
            """
            evidence_kind IN (
                'source_excerpt',
                'extracted_fact'
            )
            """,
            name="valid_evidence_kind",
        ),
        CheckConstraint(
            """
            review_status IN (
                'pending',
                'accepted',
                'rejected'
            )
            """,
            name="valid_review_status",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number >= 1",
            name="valid_page_number",
        ),
        CheckConstraint(
            "source_start_char IS NULL OR source_start_char >= 0",
            name="valid_source_start",
        ),
        CheckConstraint(
            "source_end_char IS NULL OR source_end_char >= 0",
            name="valid_source_end",
        ),
        CheckConstraint(
            """
            source_start_char IS NULL
            OR source_end_char IS NULL
            OR source_end_char >= source_start_char
            """,
            name="valid_source_offsets",
        ),
        CheckConstraint(
            """
            (
                evidence_kind = 'source_excerpt'
                AND field_name IS NULL
                AND extracted_value IS NULL
                AND extraction_hash IS NULL
            )
            OR
            (
                evidence_kind = 'extracted_fact'
                AND field_name IS NOT NULL
                AND extracted_value IS NOT NULL
                AND extraction_hash IS NOT NULL
            )
            """,
            name="valid_evidence_payload",
        ),
        CheckConstraint(
            """
            field_name IS NULL
            OR field_name IN (
                'product_name',
                'product_grade',
                'batch_number',
                'manufacturing_site',
                'process_stage',
                'incident_date',
                'affected_quantity',
                'affected_unit',
                'incident_description',
                'immediate_containment'
            )
            """,
            name="valid_extracted_field",
        ),
        ForeignKeyConstraint(
            ["source_document_id", "investigation_id"],
            [
                "source_documents.id",
                "source_documents.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "id",
            "investigation_id",
            name="uq_evidence_items_id_investigation",
        ),
        Index(
            "ix_evidence_items_investigation_created_at",
            "investigation_id",
            "created_at",
        ),
        Index(
            "ix_evidence_items_source_document",
            "source_document_id",
        ),
        Index(
            "ix_evidence_items_field_name",
            "investigation_id",
            "field_name",
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

    source_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    evidence_kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="source_excerpt",
        server_default="source_excerpt",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_start_char: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source_end_char: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    field_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    extracted_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
