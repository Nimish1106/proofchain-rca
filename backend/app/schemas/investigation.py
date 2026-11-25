from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils.date_utils import parse_incident_date


class InvestigationCreate(BaseModel):
    """Data required to create an investigation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    product_name: str | None = Field(
        default=None, max_length=200
    )
    product_grade: str | None = Field(
        default=None, max_length=100
    )
    batch_number: str | None = Field(
        default=None, max_length=100
    )
    manufacturing_site: str | None = Field(
        default=None, max_length=200
    )
    process_stage: str | None = Field(
        default=None, max_length=150
    )
    incident_date: date | None = None
    affected_quantity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )
    affected_unit: str | None = Field(
        default=None, max_length=30
    )
    incident_description: str | None = None
    immediate_containment: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty.")
        return cleaned

    @field_validator("incident_date", mode="before")
    @classmethod
    def normalize_incident_date(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return parse_incident_date(value)

    @field_validator(
        "product_name",
        "product_grade",
        "batch_number",
        "manufacturing_site",
        "process_stage",
        "affected_unit",
        "incident_description",
        "immediate_containment",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class InvestigationUpdate(BaseModel):
    """
    Partial investigation update.
    Only fields explicitly supplied by the client
    are eligible for modification.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None, max_length=200
    )
    product_name: str | None = Field(
        default=None, max_length=200
    )
    product_grade: str | None = Field(
        default=None, max_length=100
    )
    batch_number: str | None = Field(
        default=None, max_length=100
    )
    manufacturing_site: str | None = Field(
        default=None, max_length=200
    )
    process_stage: str | None = Field(
        default=None, max_length=150
    )
    incident_date: date | None = None
    affected_quantity: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=14,
        decimal_places=3,
    )
    affected_unit: str | None = Field(
        default=None, max_length=30
    )
    incident_description: str | None = None
    immediate_containment: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value is None:
            raise ValueError("Title cannot be cleared.")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty.")
        return cleaned

    @field_validator("incident_date", mode="before")
    @classmethod
    def normalize_incident_date(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return parse_incident_date(value)

    @field_validator(
        "product_name",
        "product_grade",
        "batch_number",
        "manufacturing_site",
        "process_stage",
        "affected_unit",
        "incident_description",
        "immediate_containment",
    )
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value

    @model_validator(mode="after")
    def require_at_least_one_update(self):
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided."
            )
        return self


class InvestigationRead(BaseModel):
    """Public API representation of an investigation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    status: str
    product_name: str | None
    product_grade: str | None
    batch_number: str | None
    manufacturing_site: str | None
    process_stage: str | None
    incident_date: date | None
    affected_quantity: Decimal | None
    affected_unit: str | None
    incident_description: str | None
    immediate_containment: str | None
    created_at: datetime
    updated_at: datetime


class InvestigationListResponse(BaseModel):
    """Paginated investigation list response."""

    items: list[InvestigationRead]
    total: int
    limit: int
    offset: int
