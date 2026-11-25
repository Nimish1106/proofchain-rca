import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class HypothesisEvidence(Base):
    """
    Links a root-cause hypothesis to source evidence.

    Relationship types:
    - supports
    - contradicts
    - contextual
    """

    __tablename__ = "hypothesis_evidence"

    __table_args__ = (
        CheckConstraint(
            """
            relationship_type IN (
                'supports',
                'contradicts',
                'contextual'
            )
            """,
            name="valid_relationship_type",
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
            "evidence_item_id",
            name="uq_hypothesis_evidence_pair",
        ),
        Index(
            "ix_hypothesis_evidence_investigation",
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

    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
