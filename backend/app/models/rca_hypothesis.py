import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RCAHypothesis(Base):
    """A potential cause proposed during an RCA analysis run."""

    __tablename__ = "rca_hypotheses"

    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'proposed',
                'under_review',
                'supported_by_records',
                'contradicted',
                'rejected',
                'confirmed_by_investigator'
            )
            """,
            name="valid_hypothesis_status",
        ),
        ForeignKeyConstraint(
            ["analysis_run_id", "investigation_id"],
            [
                "rca_analysis_runs.id",
                "rca_analysis_runs.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "id",
            "investigation_id",
            name="uq_rca_hypotheses_id_investigation",
        ),
        Index(
            "ix_rca_hypotheses_investigation_status",
            "investigation_id",
            "status",
        ),
        Index(
            "ix_rca_hypotheses_analysis_run",
            "analysis_run_id",
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

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    causal_mechanism: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="proposed",
        server_default="proposed",
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
