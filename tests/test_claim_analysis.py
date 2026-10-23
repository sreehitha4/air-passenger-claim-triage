
from app.models import PassengerClaim
from agents.claim_analysis import analyze_claim


def test_claim_analysis_extracts_facts():
    claim = PassengerClaim(
        claim_id="CLAIM-TEST-001",
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

    result = analyze_claim(claim)

    assert result["claim_id"] == "CLAIM-TEST-001"
    assert result["claim_facts"]["disruption_type"] == "cancellation"
    assert result["claim_facts"]["alternate_flight_taken"] is True
    assert result["missing_information"] == []
    assert result["requires_regulatory_research"] is True
    assert result["legal_conclusion"] is None


def test_missing_notification_is_flagged():
    claim = PassengerClaim(
        claim_id="CLAIM-TEST-002",
        passenger_name="Test Passenger",
        airline="Example Airways",
        flight_number="EA102",
        departure_airport="BLR",
        arrival_airport="DEL",
        scheduled_departure="2026-11-01T10:00:00+05:30",
        disruption_type="cancellation",
        notification_time=None,
        alternate_flight_taken=False,
        description="Flight cancellation reported.",
        evidence_references=[],
    )

    result = analyze_claim(claim)

    assert "notification_time" in result["missing_information"]
    assert result["legal_conclusion"] is None
