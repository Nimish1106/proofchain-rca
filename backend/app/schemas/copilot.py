"""AI Copilot schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EDITABLE_INVESTIGATION_FIELDS = {
    "title",
    "product_name",
    "product_grade",
    "batch_number",
    "manufacturing_site",
    "process_stage",
    "incident_date",
    "affected_quantity",
    "affected_unit",
    "incident_description",
    "immediate_containment",
}


class CopilotRequest(BaseModel):
    """User message to the AI Copilot."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=5000,
    )
    context_type: Literal[
        "investigation",
        "hypothesis",
        "evidence",
        "general",
    ] = "general"
    target_id: UUID | None = None


class CopilotFieldEdit(BaseModel):
    """A suggested field edit from the Copilot."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    current_value: str | None = None
    suggested_value: str
    rationale: str = ""


class CopilotApplyEditsRequest(BaseModel):
    """Explicit investigator approval to apply selected Copilot edits."""

    model_config = ConfigDict(extra="forbid")

    edits: list[CopilotFieldEdit] = Field(min_length=1, max_length=15)


class CopilotResponse(BaseModel):
    """AI Copilot response."""

    message: str
    suggested_edits: list[CopilotFieldEdit] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(
        default_factory=list
    )


COPILOT_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "suggested_edits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string",
                        "enum": sorted(EDITABLE_INVESTIGATION_FIELDS),
                    },
                    "current_value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "null"},
                        ],
                    },
                    "suggested_value": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "field_name",
                    "current_value",
                    "suggested_value",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "message",
        "suggested_edits",
        "warnings",
    ],
    "additionalProperties": False,
}
