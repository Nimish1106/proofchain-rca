from typing import Any

from app.agents.state import ExtractionState
from app.utils.date_utils import normalize_incident_date


def validate_facts(
    state: ExtractionState,
) -> dict:
    """
    Validate extracted facts against original source text.
    Rejected claims are returned with explicit reasons.
    Only source-validated facts proceed to persistence.
    """
    chunks_by_id = {
        chunk["chunk_id"]: chunk
        for chunk in state.get("chunks", [])
    }
    pages_by_key = {
        (
            page["source_document_id"],
            page["page_number"],
        ): page
        for page in state.get("source_pages", [])
    }

    validated_facts: list[dict[str, Any]] = []
    rejected_facts: list[dict[str, Any]] = []

    for fact in state.get("raw_facts", []):
        chunk = chunks_by_id.get(fact["chunk_id"])
        if chunk is None:
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": fact["extracted_value"],
                    "source_quote": fact["source_quote"],
                    "page_number": fact["page_number"],
                    "reason": "source_chunk_not_found",
                }
            )
            continue

        if fact["page_number"] != chunk["page_number"]:
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": fact["extracted_value"],
                    "source_quote": fact["source_quote"],
                    "page_number": fact["page_number"],
                    "reason": "page_reference_mismatch",
                }
            )
            continue

        page_key = (
            fact["source_document_id"],
            fact["page_number"],
        )
        source_page = pages_by_key.get(page_key)
        if source_page is None:
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": fact["extracted_value"],
                    "source_quote": fact["source_quote"],
                    "page_number": fact["page_number"],
                    "reason": "source_page_not_found",
                }
            )
            continue

        quote = fact["source_quote"]
        extracted_value = fact["extracted_value"]
        chunk_text = chunk["chunk_text"]
        quote_position = chunk_text.find(quote)

        if quote_position < 0:
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": extracted_value,
                    "source_quote": quote,
                    "page_number": fact["page_number"],
                    "reason": (
                        "quotation_not_found_in_source_chunk"
                    ),
                }
            )
            continue

        # Require a literal value match in the quotation.
        if extracted_value not in quote:
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": extracted_value,
                    "source_quote": quote,
                    "page_number": fact["page_number"],
                    "reason": "value_not_found_in_quotation",
                }
            )
            continue

        absolute_start = (
            chunk["chunk_start_char"] + quote_position
        )
        page_text = source_page["text"]
        if not page_text.startswith(
            quote,
            absolute_start,
        ):
            rejected_facts.append(
                {
                    "field_name": fact["field_name"],
                    "extracted_value": extracted_value,
                    "source_quote": quote,
                    "page_number": fact["page_number"],
                    "reason": (
                        "quotation_not_found_at_original_offset"
                    ),
                }
            )
            continue

        normalized_value = extracted_value
        if fact["field_name"] == "incident_date":
            try:
                normalized_value = normalize_incident_date(extracted_value)
            except ValueError:
                rejected_facts.append(
                    {
                        "field_name": fact["field_name"],
                        "extracted_value": extracted_value,
                        "source_quote": quote,
                        "page_number": fact["page_number"],
                        "reason": "invalid_date_format",
                    }
                )
                continue

        validated_facts.append(
            {
                "field_name": fact["field_name"],
                "extracted_value": normalized_value,
                "content": quote,
                "source_document_id": (
                    fact["source_document_id"]
                ),
                "original_filename": (
                    fact["original_filename"]
                ),
                "page_number": fact["page_number"],
                "source_start_char": absolute_start,
                "source_end_char": (
                    absolute_start + len(quote)
                ),
            }
        )

    return {
        "validated_facts": validated_facts,
        "rejected_facts": rejected_facts,
    }
