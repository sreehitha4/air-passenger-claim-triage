
from agents import graph as graph_module


def make_claim():
    return {
        "claim_id": "CLAIM-RETRY-001",
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


def test_graph_retries_after_verification_failure(monkeypatch):
    attempts = {"count": 0}
    original_verify = graph_module.verify_evidence_node

    def verify_once_fails(state):
        attempts["count"] += 1

        if attempts["count"] == 1:
            return {
                "verification_status": "failed",
                "next_action": "human_review",
                "escalation_reason": "Simulated verification failure",
            }

        return original_verify(state)

    monkeypatch.setattr(
        graph_module, "verify_evidence_node", verify_once_fails
    )

    graph = graph_module.build_claim_graph()
    result = graph.invoke({"claim": make_claim(), "retry_count": 0})

    assert attempts["count"] == 2
    assert result["verification_status"] == "verified"
    assert result["next_action"] == "complete"


def test_graph_escalates_after_retry_limit(monkeypatch):
    attempts = {"count": 0}

    def always_fail_verification(state):
        attempts["count"] += 1
        return {
            "verification_status": "failed",
            "next_action": "human_review",
            "escalation_reason": "Simulated persistent verification failure",
        }

    monkeypatch.setattr(
        graph_module, "verify_evidence_node", always_fail_verification
    )

    graph = graph_module.build_claim_graph()
    result = graph.invoke({"claim": make_claim(), "retry_count": 0})

    # One initial verification plus two retries.
    assert attempts["count"] == 3
    assert result["verification_status"] == "failed"
    assert result["next_action"] == "human_review"
    assert result["escalation_reason"] is not None
