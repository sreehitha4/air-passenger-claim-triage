
from langgraph.graph import END, START, StateGraph

from agents.nodes import (
    analyze_claim_node,
    research_claim_node,
    verify_evidence_node,
    request_evidence_node,
)
from agents.state import ClaimTriageState


MAX_RETRIES = 2


def route_after_analysis(state: ClaimTriageState) -> str:
    if state.get("next_action") == "request_evidence":
        return "request_evidence"

    return "research_claim"


def route_after_verification(state: ClaimTriageState) -> str:
    if state.get("verification_status") == "verified":
        return "complete"

    if state.get("retry_count", 0) < MAX_RETRIES:
        return "retry"

    return "human_review"


def retry_research_node(state: ClaimTriageState) -> dict:
    """Increment the retry counter before another research attempt."""
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "next_action": "retry",
    }


def build_claim_graph():
    """Build the claim-triage graph with retries and evidence requests."""
    builder = StateGraph(ClaimTriageState)

    builder.add_node("analyze_claim", analyze_claim_node)
    builder.add_node("research_claim", research_claim_node)
    builder.add_node("verify_evidence", verify_evidence_node)
    builder.add_node("retry_research", retry_research_node)
    builder.add_node("request_evidence", request_evidence_node)

    builder.add_edge(START, "analyze_claim")

    builder.add_conditional_edges(
        "analyze_claim",
        route_after_analysis,
        {
            "request_evidence": "request_evidence",
            "research_claim": "research_claim",
        },
    )

    builder.add_edge("request_evidence", END)
    builder.add_edge("research_claim", "verify_evidence")

    builder.add_conditional_edges(
        "verify_evidence",
        route_after_verification,
        {
            "complete": END,
            "retry": "retry_research",
            "human_review": END,
        },
    )

    builder.add_edge("retry_research", "research_claim")

    return builder.compile()


claim_graph = build_claim_graph()
