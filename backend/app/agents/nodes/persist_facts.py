import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.state import ExtractionState
from app.models.evidence_item import EvidenceItem


def generate_extraction_hash(
    investigation_id: str,
    fact: dict,
) -> str:
    """
    Generate a deterministic hash for one source-grounded fact.
    Includes its source location so the same value from
    different source documents remains separately traceable.
    """
    payload = {
        "investigation_id": investigation_id,
        "source_document_id": fact["source_document_id"],
        "field_name": fact["field_name"],
        "extracted_value": fact["extracted_value"],
        "page_number": fact["page_number"],
        "source_start_char": fact["source_start_char"],
        "source_end_char": fact["source_end_char"],
        "source_quote": fact["content"],
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def persist_facts(
    state: ExtractionState,
    db: Session,
) -> dict:
    """
    Persist source-validated facts.
    Existing facts are reused rather than duplicated.
    All new records remain pending human review.
    """
    investigation_id = state["investigation_id"]
    investigation_uuid = UUID(investigation_id)
    validated_facts = state.get("validated_facts", [])

    unique_facts: dict[str, dict] = {}
    duplicate_facts_count = 0

    for fact in validated_facts:
        extraction_hash = generate_extraction_hash(
            investigation_id,
            fact,
        )
        if extraction_hash in unique_facts:
            duplicate_facts_count += 1
            continue
        unique_facts[extraction_hash] = {
            **fact,
            "extraction_hash": extraction_hash,
        }

    if not unique_facts:
        return {
            "persisted_facts": [],
            "new_facts_count": 0,
            "duplicate_facts_count": duplicate_facts_count,
            "workflow_status": (
                "completed"
                if state.get("source_pages")
                else "no_extractable_text"
            ),
        }

    try:
        existing_statement = select(EvidenceItem).where(
            EvidenceItem.extraction_hash.in_(
                list(unique_facts.keys())
            )
        )
        existing_rows = (
            db.execute(existing_statement).scalars().all()
        )
        existing_by_hash = {
            item.extraction_hash: item
            for item in existing_rows
        }

        new_records = []
        for extraction_hash, fact in unique_facts.items():
            if extraction_hash in existing_by_hash:
                duplicate_facts_count += 1
                continue
            record = EvidenceItem(
                investigation_id=investigation_uuid,
                source_document_id=UUID(
                    fact["source_document_id"]
                ),
                evidence_kind="extracted_fact",
                content=fact["content"],
                page_number=fact["page_number"],
                source_start_char=(
                    fact["source_start_char"]
                ),
                source_end_char=fact["source_end_char"],
                field_name=fact["field_name"],
                extracted_value=fact["extracted_value"],
                extraction_hash=extraction_hash,
                review_status="pending",
            )
            new_records.append(record)

        if new_records:
            db.add_all(new_records)
            db.flush()

        db.commit()

        result_records = (
            list(existing_by_hash.values()) + new_records
        )
        # Return one record per unique extraction hash.
        persisted_facts = [
            {
                "id": str(record.id),
                "source_document_id": str(
                    record.source_document_id
                ),
                "field_name": record.field_name,
                "extracted_value": record.extracted_value,
                "content": record.content,
                "page_number": record.page_number,
                "source_start_char": record.source_start_char,
                "source_end_char": record.source_end_char,
                "review_status": record.review_status,
            }
            for record in result_records
        ]

        return {
            "persisted_facts": persisted_facts,
            "new_facts_count": len(new_records),
            "duplicate_facts_count": duplicate_facts_count,
            "workflow_status": (
                "completed"
                if state.get("source_pages")
                else "no_extractable_text"
            ),
        }
    except Exception:
        db.rollback()
        raise
