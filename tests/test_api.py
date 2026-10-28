
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


def delay_claim_missing_departure():
    claim = valid_claim()
    claim.update({
        "claim_id": "CLAIM-API-DELAY-001",
        "disruption_type": "delay",
        "notification_time": None,
        "actual_departure": None,
        "alternate_flight_taken": False,
        "alternate_flight_delay_hours": None,
        "description": (
            "The actual departure was delayed, but the exact time is unknown."
        ),
    })
    return claim


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


def test_invalid_disruption_type_is_rejected_by_api():
    claim = valid_claim()
    claim["disruption_type"] = "imaginary_disruption"

    response = client.post("/claims/validate", json=claim)

    assert response.status_code == 422


def test_negative_alternate_flight_delay_is_rejected_by_api():
    claim = valid_claim()
    claim["alternate_flight_delay_hours"] = -1

    response = client.post("/claims/validate", json=claim)

    assert response.status_code == 422


def test_description_exceeding_maximum_length_is_rejected():
    claim = valid_claim()
    claim["description"] = "x" * 5001

    response = client.post("/claims/validate", json=claim)

    assert response.status_code == 422


def test_triage_endpoint_requests_missing_delay_departure_evidence():
    response = client.post(
        "/claims/triage",
        json=delay_claim_missing_departure(),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["claim_id"] == "CLAIM-API-DELAY-001"
    assert body["next_action"] == "request_evidence"
    assert "actual_departure" in body["missing_information"]
    assert body["evidence_request"]
    assert body.get("recommendation") is None

from unittest.mock import patch

from app.jobs import process_job, submit_job


def test_submit_claim_returns_accepted_response():
    with patch("app.main.process_job") as mocked_process:
        response = client.post(
            "/claims/submit",
            json=valid_claim(),
        )

    assert response.status_code == 202

    body = response.json()
    assert body["claim_id"] == "CLAIM-API-001"
    assert body["status"] == "queued"
    assert body["job_id"]
    assert body["status_url"] == f"/jobs/{body['job_id']}"

    mocked_process.assert_called_once()


def test_get_job_returns_404_for_unknown_job():
    response = client.get("/jobs/nonexistent-job-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found."


def test_get_job_returns_completed_result():
    claim = valid_claim()
    job_id = submit_job(claim)

    expected_result = {
        "claim_id": claim["claim_id"],
        "next_action": "complete",
        "verification_status": "verified",
    }

    with patch(
        "app.jobs.claim_graph.invoke",
        return_value=expected_result,
    ):
        process_job(job_id, claim)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["job_id"] == job_id
    assert body["claim_id"] == claim["claim_id"]
    assert body["status"] == "completed"
    assert body["result"] == expected_result
    assert body["error"] is None


def test_get_job_returns_failed_status_and_safe_error():
    claim = valid_claim()
    job_id = submit_job(claim)

    with patch(
        "app.jobs.claim_graph.invoke",
        side_effect=RuntimeError("Internal diagnostic details"),
    ):
        process_job(job_id, claim)

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "failed"
    assert body["result"] is None
    assert body["error"] == (
        "The claim triage workflow could not be completed."
    )
    assert "Internal diagnostic details" not in str(body)
