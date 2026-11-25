from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.nodes.detect_conflicts import (
    detect_conflicts,
)
from app.agents.nodes.extract_facts import extract_facts
from app.agents.nodes.load_sources import load_sources
from app.agents.nodes.persist_facts import persist_facts
from app.agents.nodes.validate_facts import validate_facts
from app.agents.state import ExtractionState
from app.core.config import Settings


def build_extraction_graph(
    db: Session,
    settings: Settings,
):
    """
    Build and compile the document extraction graph.
    Database session and configuration are injected into
    node closures and are not stored in graph state.
    """
    workflow = StateGraph(ExtractionState)

    def load_node(state: ExtractionState) -> dict:
        return load_sources(
            state=state,
            db=db,
        )

    def extraction_node(state: ExtractionState) -> dict:
        return extract_facts(
            state=state,
            settings=settings,
        )

    def validation_node(state: ExtractionState) -> dict:
        return validate_facts(state)

    def conflict_node(state: ExtractionState) -> dict:
        return detect_conflicts(state)

    def persistence_node(state: ExtractionState) -> dict:
        return persist_facts(
            state=state,
            db=db,
        )

    workflow.add_node("load_sources", load_node)
    workflow.add_node("extract_facts", extraction_node)
    workflow.add_node("validate_facts", validation_node)
    workflow.add_node("detect_conflicts", conflict_node)
    workflow.add_node("persist_facts", persistence_node)

    workflow.add_edge(START, "load_sources")
    workflow.add_edge("load_sources", "extract_facts")
    workflow.add_edge("extract_facts", "validate_facts")
    workflow.add_edge("validate_facts", "detect_conflicts")
    workflow.add_edge("detect_conflicts", "persist_facts")
    workflow.add_edge("persist_facts", END)

    return workflow.compile()
