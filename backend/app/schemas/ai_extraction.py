from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


ExtractionField = Literal[
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
]


class ExtractedFact(BaseModel):
    """One source-grounded candidate fact."""

    model_config = ConfigDict(extra="forbid")

    field_name: ExtractionField

    extracted_value: str = Field(
        min_length=1,
        max_length=2000,
    )

    source_quote: str = Field(
        min_length=1,
        max_length=5000,
    )

    page_number: int = Field(ge=1)

    @field_validator(
        "extracted_value",
        "source_quote",
    )
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(
                "Extracted values cannot be blank."
            )
        return cleaned


class IncidentExtraction(BaseModel):
    """Complete structured extraction response."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(
        min_length=1,
        max_length=3000,
    )

    facts: list[ExtractedFact] = Field(
        max_length=100,
    )

    warnings: list[str] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(
                "Extraction summary cannot be empty."
            )
        return cleaned


INCIDENT_EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
        },
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field_name": {
                        "type": "string",
                        "enum": [
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
                        ],
                    },
                    "extracted_value": {
                        "type": "string",
                    },
                    "source_quote": {
                        "type": "string",
                    },
                    "page_number": {
                        "type": "integer",
                    },
                },
                "required": [
                    "field_name",
                    "extracted_value",
                    "source_quote",
                    "page_number",
                ],
                "additionalProperties": False,
            },
        },
        "warnings": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "required": [
        "summary",
        "facts",
        "warnings",
    ],
    "additionalProperties": False,
}
