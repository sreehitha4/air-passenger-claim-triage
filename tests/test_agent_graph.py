
from datetime import datetime

from agents.graph import claim_graph


def make_cancellation_claim():
    return {
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


def test_graph_analyzes_claim():
    result = claim_graph.invoke({
        "claim": make_cancellation_claim(),
        "retry_count": 0,
    })

    # Claim analysis
    assert result["claim_id"] == "CLAIM-GRAPH-001"
    assert result["claim_facts"]["disruption_type"] == "cancellation"
    assert result["missing_information"] == []

    # Research and retrieval verification
    assert result["next_action"] == "complete"
    assert result["verification_status"] == "verified"
    assert len(result["retrieved_passages"]) > 0
    assert len(result["applicable_provisions"]) > 0
    assert result["escalation_reason"] is None

    # Evidence assessments must be present in the final graph state.
    assert len(result["clause_assessments"]) > 0

    for assessment in result["clause_assessments"]:
        assert "conditions_to_review" in assessment
        assert assessment["condition_review_status"] == "not_assessed"
        assert assessment["legal_conclusion"] is None

    # Retrieval success must not be treated as legal eligibility.
    assert result.get("recommendation") is None


def test_graph_preserves_cancellation_timing_facts():
    result = claim_graph.invoke({
        "claim": make_cancellation_claim(),
        "retry_count": 0,
    })

    facts = result["claim_facts"]
    scheduled = datetime.fromisoformat(facts["scheduled_departure"])
    notified = datetime.fromisoformat(facts["notification_time"])

    notification_minutes = (
        scheduled - notified
    ).total_seconds() / 60

    assert notification_minutes == 90
    assert facts["alternate_flight_taken"] is True
    assert facts["alternate_flight_delay_hours"] == 4
    assert result.get("recommendation") is None


def test_graph_escalates_after_repeated_verification_failures(monkeypatch):
    import agents.nodes as nodes

    def return_no_provisions(*args, **kwargs):
        return []

    monkeypatch.setattr(
        nodes.RegulatoryRetrieval,
        "get_clause",
        return_no_provisions,
    )

    result = claim_graph.invoke({
        "claim": make_cancellation_claim(),
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert result["next_action"] == "human_review"
    assert result["retry_count"] == 2
    assert result["escalation_reason"] is not None
    assert "required candidate clause headings" in result["escalation_reason"]
    assert result.get("recommendation") is None


def test_graph_escalates_when_clause_heading_mismatches_citation(
    monkeypatch,
):
    import agents.nodes as nodes

    def return_mismatched_clause(*args, **kwargs):
        return [
            {
                "clause_number": "3.3.1",
                "source": "dgca_car_revision_4.pdf",
                "page": 5,
                "text": "3.3.2 This text deliberately has a mismatched heading.",
            }
        ]

    monkeypatch.setattr(
        nodes.RegulatoryRetrieval,
        "get_clause",
        return_mismatched_clause,
    )

    result = claim_graph.invoke({
        "claim": make_cancellation_claim(),
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert result["next_action"] == "human_review"
    assert result["retry_count"] == 2
    assert result["escalation_reason"] is not None
    assert result.get("recommendation") is None
