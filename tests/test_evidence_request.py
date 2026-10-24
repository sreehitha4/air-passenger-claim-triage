
from agents.graph import claim_graph


def test_graph_requests_missing_cancellation_information():
    claim = {
        "claim_id": "CLAIM-EVIDENCE-001",
        "passenger_name": "Test Passenger",
        "airline": "Example Airways",
        "flight_number": "EA101",
        "departure_airport": "BLR",
        "arrival_airport": "DEL",
        "scheduled_departure": "2026-11-01T10:00:00+05:30",
        "disruption_type": "cancellation",
        "notification_time": None,
        "actual_departure": None,
        "alternate_flight_taken": False,
        "alternate_flight_delay_hours": None,
        "description": "My flight was cancelled.",
        "evidence_references": [],
    }

    result = claim_graph.invoke({
        "claim": claim,
        "retry_count": 0,
    })

    assert result["claim_id"] == "CLAIM-EVIDENCE-001"
    assert "notification_time" in result["missing_information"]
    assert result["next_action"] == "request_evidence"
    assert len(result["evidence_request"]) > 0
    assert any(
        "informed you" in question.lower()
        for question in result["evidence_request"]
    )
    assert result.get("verification_status") == "pending"
