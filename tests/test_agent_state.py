
from agents.state import ClaimTriageState


def test_state_accepts_initial_claim_data():
    state: ClaimTriageState = {
        "claim_id": "CLAIM-TEST-001",
        "claim": {"disruption_type": "cancellation"},
        "claim_facts": {"disruption_type": "cancellation"},
        "missing_information": [],
        "retry_count": 0,
        "verification_status": "pending",
        "next_action": "research",
    }

    assert state["claim_id"] == "CLAIM-TEST-001"
    assert state["retry_count"] == 0
    assert state["verification_status"] == "pending"
    assert state["next_action"] == "research"
