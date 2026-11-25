import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RCAAnalysisRun(Base):
    """
    One execution of an RCA analysis workflow.

    Each run records its input fingerprint, model identity,
    execution status and generated summary.
    """

    __tablename__ = "rca_analysis_runs"

    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'running',
                'completed',
                'failed'
            )
            """,
            name="valid_analysis_run_status",
        ),
        UniqueConstraint(
            "id",
            "investigation_id",
            name="uq_rca_analysis_runs_id_investigation",
        ),
        Index(
            "ix_rca_analysis_runs_investigation_created_at",
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

    model_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    input_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="running",
        server_default="running",
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
