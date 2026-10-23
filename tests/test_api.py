
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def valid_claim():
    return {
        "claim_id": "CLAIM-API-001",
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


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_valid_claim_endpoint():
    response = client.post(
        "/claims/validate",
        json=valid_claim(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "validated"
    assert response.json()["claim_id"] == "CLAIM-API-001"


def test_missing_field_is_rejected_by_api():
    claim = valid_claim()
    claim.pop("flight_number")

    response = client.post("/claims/validate", json=claim)

    assert response.status_code == 422


def test_unknown_field_is_rejected_by_api():
    claim = valid_claim()
    claim["unexpected_field"] = "not allowed"

    response = client.post("/claims/validate", json=claim)

    assert response.status_code == 422
