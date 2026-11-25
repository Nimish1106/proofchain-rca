from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.graph import build_extraction_graph
from app.core.config import Settings


def run_document_extraction(
    db: Session,
    investigation_id: UUID,
    settings: Settings,
) -> dict:
    """
    Execute the complete source-grounded extraction workflow.
    The graph is compiled for this request and receives only
    the investigation identifier as its initial state.
    """
    graph = build_extraction_graph(
        db=db,
        settings=settings,
    )
    result = graph.invoke(
        {
            "investigation_id": str(investigation_id),
        }
    )
    return result
