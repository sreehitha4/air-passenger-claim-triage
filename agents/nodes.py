
from app.models import PassengerClaim
from agents.claim_analysis import analyze_claim
from agents.state import ClaimTriageState


def analyze_claim_node(state: ClaimTriageState) -> dict:
    """Analyze a validated claim and update the workflow state."""

    claim = PassengerClaim.model_validate(state["claim"])
    analysis = analyze_claim(claim)

    if analysis["missing_information"]:
        next_action = "request_evidence"
    else:
        next_action = "research"

    return {
        "claim_id": analysis["claim_id"],
        "claim_facts": analysis["claim_facts"],
        "missing_information": analysis["missing_information"],
        "next_action": next_action,
        "retry_count": state.get("retry_count", 0),
        "verification_status": "pending",
    }
