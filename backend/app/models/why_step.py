import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class WhyStep(Base):
    """
    One step in a five-whys causal investigation.

    Each answer must distinguish documented information
    from hypotheses and unanswered questions.
    """

    __tablename__ = "why_steps"

    __table_args__ = (
        CheckConstraint(
            "step_number BETWEEN 1 AND 5",
            name="valid_step_number",
        ),
        CheckConstraint(
            """
            answer_basis IN (
                'source_supported',
                'hypothesis',
                'unknown'
            )
            """,
            name="valid_answer_basis",
        ),
        CheckConstraint(
            """
            (
                answer_basis = 'source_supported'
                AND evidence_item_id IS NOT NULL
            )
            OR
            (
                answer_basis IN ('hypothesis', 'unknown')
                AND evidence_item_id IS NULL
            )
            """,
            name="valid_answer_evidence",
        ),
        ForeignKeyConstraint(
            ["hypothesis_id", "investigation_id"],
            [
                "rca_hypotheses.id",
                "rca_hypotheses.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["evidence_item_id", "investigation_id"],
            [
                "evidence_items.id",
                "evidence_items.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "hypothesis_id",
            "step_number",
            name="uq_why_steps_hypothesis_step",
        ),
        Index(
            "ix_why_steps_investigation",
            "investigation_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    answer_basis: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )

    evidence_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
