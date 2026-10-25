
from agents.graph import claim_graph


def make_cancellation_claim():
    return {
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


def test_graph_requests_missing_cancellation_information():
    claim = make_cancellation_claim()

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


def test_graph_requests_all_missing_cancellation_information():
    claim = make_cancellation_claim()
    claim.update({
        "claim_id": "CLAIM-EVIDENCE-002",
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": None,
        "description": (
            "My flight was cancelled and I took an alternate flight, "
            "but I do not know the delay details."
        ),
    })

    result = claim_graph.invoke({
        "claim": claim,
        "retry_count": 0,
    })

    # Both missing fields must be identified.
    assert result["claim_id"] == "CLAIM-EVIDENCE-002"
    assert "notification_time" in result["missing_information"]
    assert "alternate_flight_delay_hours" in result["missing_information"]

    # The workflow must ask for evidence instead of proceeding to research.
    assert result["next_action"] == "request_evidence"
    assert len(result["evidence_request"]) >= 2
    assert all(
        isinstance(question, str) and question.strip()
        for question in result["evidence_request"]
    )

    # The workflow must preserve relevant facts without making a decision.
    assert result["claim_facts"]["alternate_flight_taken"] is True
    assert result["claim_facts"]["alternate_flight_delay_hours"] is None
    assert result.get("verification_status") == "pending"
    assert result.get("recommendation") is None
