from langgraph.graph import END, START, StateGraph

from app.agents.nodes.analyze_hypotheses import analyze_hypotheses
from app.agents.nodes.generate_hypotheses import generate_hypotheses
from app.agents.nodes.validate_rca import validate_rca
from app.agents.rca_state import RCAState


def build_rca_graph():
    """
    Build the evidence-first RCA reasoning graph.

    This graph has no database session and performs no persistence.
    Its only responsibility is to generate and validate RCA output.
    """
    workflow = StateGraph(RCAState)

    workflow.add_node("generate_hypotheses", generate_hypotheses)
    workflow.add_node("analyze_hypotheses", analyze_hypotheses)
    workflow.add_node("validate_rca", validate_rca)

    workflow.add_edge(START, "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "analyze_hypotheses")
    workflow.add_edge("analyze_hypotheses", "validate_rca")
    workflow.add_edge("validate_rca", END)

    return workflow.compile()
