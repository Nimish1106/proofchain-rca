import pytest
from pydantic import ValidationError

from app.schemas.ai_extraction import (
    ExtractedFact,
    IncidentExtraction,
)


def test_valid_extracted_fact():
    fact = ExtractedFact(
        field_name="batch_number",
        extracted_value="MTF26001",
        source_quote="Batch Number: MTF26001",
        page_number=1,
    )
    assert fact.field_name == "batch_number"
    assert fact.extracted_value == "MTF26001"
    assert fact.page_number == 1


def test_extraction_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ExtractedFact(
            field_name="customer_name",
            extracted_value="Example Ltd.",
            source_quote="Customer: Example Ltd.",
            page_number=1,
        )


def test_extraction_rejects_invalid_page():
    with pytest.raises(ValidationError):
        ExtractedFact(
            field_name="batch_number",
            extracted_value="MTF26001",
            source_quote="Batch Number: MTF26001",
            page_number=0,
        )


def test_extraction_rejects_blank_quote():
    with pytest.raises(ValidationError):
        ExtractedFact(
            field_name="batch_number",
            extracted_value="MTF26001",
            source_quote="   ",
            page_number=1,
        )


def test_extraction_allows_missing_fields():
    result = IncidentExtraction(
        summary="Batch information extracted.",
        facts=[],
        warnings=[
            "Manufacturing date not found."
        ],
    )
    assert result.facts == []
    assert len(result.warnings) == 1


def test_extraction_rejects_unknown_properties():
    with pytest.raises(ValidationError):
        ExtractedFact(
            field_name="batch_number",
            extracted_value="MTF26001",
            source_quote="Batch Number: MTF26001",
            page_number=1,
            confidence=0.99,
        )
