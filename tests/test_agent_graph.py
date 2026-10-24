
from agents.graph import claim_graph


def test_graph_analyzes_claim():
    claim = {
        "claim_id": "CLAIM-GRAPH-001",
        "passenger_name": "Test Passenger",
        "airline": "Example Airways",
        "flight_number": "EA101",
        "departure_airport": "BLR",
        "arrival_airport": "DEL",
        "scheduled_departure": "2026-11-01T10:00:00+05:30",
        "disruption_type": "cancellation",
        "notification_time": "2026-11-01T08:30:00+05:30",
        "actual_departure": None,
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": 4,
        "description": "Flight cancelled before departure.",
        "evidence_references": [],
    }

    result = claim_graph.invoke({
        "claim": claim,
        "retry_count": 0,
    })

    # Claim analysis
    assert result["claim_id"] == "CLAIM-GRAPH-001"
    assert result["claim_facts"]["disruption_type"] == "cancellation"
    assert result["missing_information"] == []

    # Research and verification
    assert result["next_action"] == "complete"
    assert result["verification_status"] == "verified"
    assert len(result["retrieved_passages"]) > 0
    assert len(result["applicable_provisions"]) > 0
    assert result["escalation_reason"] is None
