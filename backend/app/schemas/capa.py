"""CAPA (Corrective and Preventive Action) schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CAPAProposal(BaseModel):
    """AI-generated CAPA recommendation (from structured output)."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_key: Literal["H1", "H2", "H3"]
    capa_type: Literal["corrective", "preventive"]
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=5000)
    expected_outcome: str | None
    verification_method: str | None
    effectiveness_criteria: str | None
    priority: Literal["low", "medium", "high", "critical"]
    residual_risk: str | None


class CAPAGenerationOutput(BaseModel):
    """Structured output from CAPA generation."""

    model_config = ConfigDict(extra="forbid")

    recommendations: list[CAPAProposal] = Field(
        max_length=20,
    )
    summary: str = Field(
        min_length=1,
        max_length=3000,
    )
    warnings: list[str] = Field(
        max_length=50,
    )


class CAPARead(BaseModel):
    """Public CAPA representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    investigation_id: UUID
    hypothesis_id: UUID
    capa_type: str
    title: str
    description: str
    expected_outcome: str | None
    verification_method: str | None
    effectiveness_criteria: str | None
    priority: str
    residual_risk: str | None
    status: str
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class CAPAListResponse(BaseModel):
    """List of CAPA recommendations."""

    items: list[CAPARead]
    total: int


class CAPAStatusUpdate(BaseModel):
    """Update CAPA status."""

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "proposed",
        "approved",
        "in_progress",
        "completed",
        "rejected",
    ]
    review_note: str | None = None


CAPA_GENERATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "maxItems": 20,
            "items": {
                "type": "object",
                "properties": {
                    "hypothesis_key": {
                        "type": "string",
                        "enum": ["H1", "H2", "H3"],
                    },
                    "capa_type": {
                        "type": "string",
                        "enum": [
                            "corrective",
                            "preventive",
                        ],
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "expected_outcome": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "verification_method": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "effectiveness_criteria": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "priority": {
                        "type": "string",
                        "enum": [
                            "low",
                            "medium",
                            "high",
                            "critical",
                        ],
                    },
                    "residual_risk": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                },
                "required": [
                    "hypothesis_key",
                    "capa_type",
                    "title",
                    "description",
                    "expected_outcome",
                    "verification_method",
                    "effectiveness_criteria",
                    "priority",
                    "residual_risk",
                ],
                "additionalProperties": False,
            },
        },
        "summary": {"type": "string"},
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "recommendations",
        "summary",
        "warnings",
    ],
    "additionalProperties": False,
}
