
import pytest
from pydantic import ValidationError

from app.models import DisruptionType, PassengerClaim


@pytest.fixture
def valid_claim_data():
    return {
        "claim_id": "CLAIM-001",
        "passenger_name": "Test Passenger",
        "airline": "Example Airways",
        "flight_number": "EA101",
        "departure_airport": "BLR",
        "arrival_airport": "DEL",
        "scheduled_departure": "2026-11-01T10:00:00+05:30",
        "disruption_type": "cancellation",
        "notification_time": "2026-11-01T08:30:00+05:30",
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": 4,
        "description": "Flight cancelled shortly before departure.",
        "evidence_references": [],
    }


def test_valid_claim_is_accepted(valid_claim_data):
    claim = PassengerClaim.model_validate(valid_claim_data)

    assert claim.claim_id == "CLAIM-001"
    assert claim.disruption_type == DisruptionType.CANCELLATION


def test_missing_required_field_is_rejected(valid_claim_data):
    valid_claim_data.pop("flight_number")

    with pytest.raises(ValidationError):
        PassengerClaim.model_validate(valid_claim_data)


def test_unknown_field_is_rejected(valid_claim_data):
    valid_claim_data["unexpected_field"] = "not allowed"

    with pytest.raises(ValidationError):
        PassengerClaim.model_validate(valid_claim_data)


def test_notification_after_departure_is_rejected(valid_claim_data):
    valid_claim_data["notification_time"] = (
        "2026-11-01T10:30:00+05:30"
    )

    with pytest.raises(ValidationError):
        PassengerClaim.model_validate(valid_claim_data)
