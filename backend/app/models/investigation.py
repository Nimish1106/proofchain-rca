import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Investigation(Base):
    """
    Represents an API pharmaceutical quality investigation.
    """

    __tablename__ = "investigations"

    __table_args__ = (
        CheckConstraint(
            """
            status IN (
                'draft',
                'processing',
                'in_progress',
                'in_review',
                'completed',
                'cancelled'
            )
            """,
            name="valid_status",
        ),
        CheckConstraint(
            "affected_quantity IS NULL OR affected_quantity > 0",
            name="valid_affected_quantity",
        ),
        Index(
            "ix_investigations_batch_number",
            "batch_number",
        ),
        Index(
            "ix_investigations_status_created_at",
            "status",
            "created_at",
        ),
    )

    # Primary identity
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Investigation details
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    # Product information
    product_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    product_grade: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    batch_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Manufacturing information
    manufacturing_site: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    process_stage: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    incident_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Impact information
    affected_quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 3),
        nullable=True,
    )

    affected_unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    # Incident description
    incident_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    immediate_containment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
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

    def __repr__(self) -> str:
        return (
            f"Investigation("
            f"id={self.id}, "
            f"status={self.status!r}"
            f")"
        )
