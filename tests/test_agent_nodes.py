
from app.models import PassengerClaim
from agents.nodes import analyze_claim_node


def test_analysis_node_routes_complete_claim_to_research():
    claim = PassengerClaim(
        claim_id="CLAIM-NODE-001",
        passenger_name="Test Passenger",
        airline="Example Airways",
        flight_number="EA101",
        departure_airport="BLR",
        arrival_airport="DEL",
        scheduled_departure="2026-11-01T10:00:00+05:30",
        disruption_type="cancellation",
        notification_time="2026-11-01T08:30:00+05:30",
        alternate_flight_taken=True,
        alternate_flight_delay_hours=4,
        description="Flight cancelled before departure.",
        evidence_references=[],
    )

    result = analyze_claim_node({
        "claim": claim.model_dump(mode="json"),
        "retry_count": 0,
    })

    assert result["claim_id"] == "CLAIM-NODE-001"
    assert result["claim_facts"]["disruption_type"] == "cancellation"
    assert result["missing_information"] == []
    assert result["next_action"] == "research"
    assert result["verification_status"] == "pending"
