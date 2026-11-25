import re
from collections import defaultdict

from app.agents.state import ExtractionState

# Fields that normally represent one value for an investigation.
# Narrative fields are intentionally excluded because multiple
# valid observations or containment descriptions can exist.
SINGLE_VALUE_FIELDS = {
    "product_name",
    "product_grade",
    "batch_number",
    "manufacturing_site",
    "process_stage",
    "incident_date",
    "affected_quantity",
    "affected_unit",
}


def normalize_for_comparison(value: str) -> str:
    """Normalize whitespace and case for comparison only."""
    return re.sub(
        r"\s+",
        " ",
        value.strip(),
    ).casefold()


def detect_conflicts(
    state: ExtractionState,
) -> dict:
    """
    Detect multiple different values for single-value fields.
    No source fact is deleted or automatically selected.
    """
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for fact in state.get("validated_facts", []):
        field_name = fact["field_name"]
        if field_name not in SINGLE_VALUE_FIELDS:
            continue

        normalized_value = normalize_for_comparison(
            fact["extracted_value"]
        )
        grouped[field_name][normalized_value].append(
            {
                "value": fact["extracted_value"],
                "source_document_id": (
                    fact["source_document_id"]
                ),
                "original_filename": (
                    fact["original_filename"]
                ),
                "page_number": fact["page_number"],
                "source_quote": fact["content"],
            }
        )

    conflicts = []
    for field_name, value_groups in grouped.items():
        if len(value_groups) <= 1:
            continue
        candidates = []
        for candidate_group in value_groups.values():
            candidates.extend(candidate_group)
        conflicts.append(
            {
                "field_name": field_name,
                "status": "requires_human_resolution",
                "candidates": candidates,
            }
        )

    warnings = list(state.get("warnings", []))
    for conflict in conflicts:
        warnings.append(
            f"Multiple source values found for "
            f"{conflict['field_name']}. "
            "Human resolution is required."
        )

    return {
        "field_conflicts": conflicts,
        "warnings": list(dict.fromkeys(warnings)),
    }
