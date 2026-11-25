from typing import Any

from typing_extensions import NotRequired, TypedDict


class ExtractionState(TypedDict):
    """
    Shared state for the pharmaceutical document extraction graph.
    Only investigation_id is required as initial input.
    Each node returns the fields it updates.
    """

    investigation_id: str
    source_pages: NotRequired[list[dict[str, Any]]]
    chunks: NotRequired[list[dict[str, Any]]]
    raw_facts: NotRequired[list[dict[str, Any]]]
    validated_facts: NotRequired[list[dict[str, Any]]]
    rejected_facts: NotRequired[list[dict[str, Any]]]
    field_conflicts: NotRequired[list[dict[str, Any]]]
    persisted_facts: NotRequired[list[dict[str, Any]]]
    summaries: NotRequired[list[str]]
    warnings: NotRequired[list[str]]
    new_facts_count: NotRequired[int]
    duplicate_facts_count: NotRequired[int]
    workflow_status: NotRequired[str]
