
from app.models import PassengerClaim
from agents.claim_analysis import analyze_claim


def make_claim(**overrides):
    data = {
        "claim_id": "CLAIM-TEST-001",
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
    data.update(overrides)
    return PassengerClaim(**data)


def test_claim_analysis_extracts_facts():
    result = analyze_claim(make_claim())

    assert result["claim_id"] == "CLAIM-TEST-001"
    assert result["claim_facts"]["disruption_type"] == "cancellation"
    assert result["claim_facts"]["alternate_flight_taken"] is True
    assert result["missing_information"] == []
    assert result["requires_regulatory_research"] is True
    assert result["legal_conclusion"] is None


def test_missing_notification_is_flagged_for_cancellation():
    claim = make_claim(
        notification_time=None,
        alternate_flight_taken=False,
    )

    result = analyze_claim(claim)

    assert "notification_time" in result["missing_information"]
    assert result["legal_conclusion"] is None


def test_missing_alternate_delay_is_flagged():
    claim = make_claim(alternate_flight_delay_hours=None)

    result = analyze_claim(claim)

    assert "alternate_flight_delay_hours" in result["missing_information"]


def test_delay_claim_without_actual_departure_is_flagged():
    claim = make_claim(
        disruption_type="delay",
        actual_departure=None,
        alternate_flight_taken=False,
        alternate_flight_delay_hours=None,
        description="The flight was delayed.",
    )

    result = analyze_claim(claim)

    assert "actual_departure" in result["missing_information"]


def test_non_cancellation_does_not_require_cancellation_notification():
    claim = make_claim(
        disruption_type="denied_boarding",
        notification_time=None,
        alternate_flight_taken=False,
        alternate_flight_delay_hours=None,
    )

    result = analyze_claim(claim)

    assert "notification_time" not in result["missing_information"]
    assert result["legal_conclusion"] is None
