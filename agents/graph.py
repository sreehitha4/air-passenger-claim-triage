
from langgraph.graph import END, START, StateGraph

from agents.nodes import analyze_claim_node
from agents.state import ClaimTriageState


def build_claim_graph():
    """
    Build the initial claim-triage graph.

    Currently, the graph runs claim analysis only.
    Regulatory research will be added in a later step.
    """

    builder = StateGraph(ClaimTriageState)

    builder.add_node("analyze_claim", analyze_claim_node)

    builder.add_edge(START, "analyze_claim")
    builder.add_edge("analyze_claim", END)

    return builder.compile()


claim_graph = build_claim_graph()
