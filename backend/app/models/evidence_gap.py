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
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class EvidenceGap(Base):
    """An unresolved information requirement in an RCA run."""

    __tablename__ = "evidence_gaps"

    __table_args__ = (
        CheckConstraint(
            """
            gap_type IN (
                'missing_record',
                'conflicting_information',
                'unverified_hypothesis',
                'insufficient_detail',
                'other'
            )
            """,
            name="valid_gap_type",
        ),
        CheckConstraint(
            """
            priority IN (
                'low',
                'medium',
                'high'
            )
            """,
            name="valid_gap_priority",
        ),
        CheckConstraint(
            """
            status IN (
                'open',
                'addressed',
                'waived'
            )
            """,
            name="valid_gap_status",
        ),
        ForeignKeyConstraint(
            ["analysis_run_id", "investigation_id"],
            [
                "rca_analysis_runs.id",
                "rca_analysis_runs.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["hypothesis_id", "investigation_id"],
            [
                "rca_hypotheses.id",
                "rca_hypotheses.investigation_id",
            ],
            ondelete="CASCADE",
        ),
        Index(
            "ix_evidence_gaps_investigation_status",
            "investigation_id",
            "status",
        ),
        Index(
            "ix_evidence_gaps_analysis_run",
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

    hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )

    gap_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_question: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        server_default="medium",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        server_default="open",
    )

    resolution_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
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
