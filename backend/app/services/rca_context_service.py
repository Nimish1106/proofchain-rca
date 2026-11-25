import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.evidence_item import EvidenceItem
from app.models.investigation import Investigation
from app.models.source_document import SourceDocument
from app.services.exceptions import (
    InvestigationNotFoundError,
    NoRCAEvidenceError,
    RCAContextLimitError,
)


@dataclass(frozen=True)
class RCAContext:
    """Immutable input supplied to one RCA analysis run."""

    investigation_id: UUID
    evidence_items: list[dict]
    input_fingerprint: str
    total_context_chars: int


def generate_context_fingerprint(
    evidence_items: list[dict],
) -> str:
    """
    Generate a deterministic SHA-256 fingerprint.
    Changes to evidence content or source associations
    produce a different fingerprint.
    """
    canonical_data = [
        {
            "id": item["evidence_id"],
            "source_document_id": item["source_document_id"],
            "evidence_kind": item["evidence_kind"],
            "content": item["content"],
            "page_number": item["page_number"],
            "field_name": item["field_name"],
            "extracted_value": item["extracted_value"],
            "review_status": item["review_status"],
        }
        for item in evidence_items
    ]
    serialized = json.dumps(
        canonical_data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def build_rca_context(
    db: Session,
    investigation_id: UUID,
    settings: Settings,
) -> RCAContext:
    """
    Load bounded source-grounded evidence for RCA.
    Does not modify investigation or evidence records.
    """
    investigation = db.get(
        Investigation,
        investigation_id,
    )
    if investigation is None:
        raise InvestigationNotFoundError(
            "Investigation not found."
        )

    statement = (
        select(
            EvidenceItem,
            SourceDocument.original_filename,
        )
        .join(
            SourceDocument,
            SourceDocument.id
            == EvidenceItem.source_document_id,
        )
        .where(
            EvidenceItem.investigation_id
            == investigation_id,
        )
        .order_by(
            SourceDocument.created_at.asc(),
            SourceDocument.id.asc(),
            EvidenceItem.page_number.asc().nulls_last(),
            EvidenceItem.id.asc(),
        )
    )
    rows = db.execute(statement).all()

    if not rows:
        raise NoRCAEvidenceError(
            "No source evidence is available for RCA. "
            "Upload and process investigation documents first."
        )

    if len(rows) > settings.rca_max_evidence_items:
        raise RCAContextLimitError(
            "The investigation contains more evidence items "
            "than the configured RCA limit. "
            "Review or scope the evidence set."
        )

    evidence_items = []
    total_context_chars = 0

    for evidence, filename in rows:
        content = evidence.content
        item = {
            "evidence_id": str(evidence.id),
            "investigation_id": str(
                evidence.investigation_id
            ),
            "source_document_id": str(
                evidence.source_document_id
            ),
            "original_filename": filename,
            "evidence_kind": evidence.evidence_kind,
            "content": content,
            "page_number": evidence.page_number,
            "field_name": evidence.field_name,
            "extracted_value": evidence.extracted_value,
            "review_status": evidence.review_status,
        }
        total_context_chars += len(content)
        total_context_chars += len(
            evidence.extracted_value or ""
        )
        if (
            total_context_chars
            > settings.rca_max_context_chars
        ):
            raise RCAContextLimitError(
                "The investigation evidence exceeds the "
                "configured RCA context limit."
            )
        evidence_items.append(item)

    fingerprint = generate_context_fingerprint(
        evidence_items
    )
    return RCAContext(
        investigation_id=investigation_id,
        evidence_items=evidence_items,
        input_fingerprint=fingerprint,
        total_context_chars=total_context_chars,
    )
