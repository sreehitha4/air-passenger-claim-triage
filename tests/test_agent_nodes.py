
from app.models import PassengerClaim
from agents.nodes import analyze_claim_node, verify_evidence_node


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


def test_verification_rejects_missing_required_clauses():
    result = verify_evidence_node({
        "claim_facts": {"disruption_type": "cancellation"},
        "applicable_provisions": [],
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert "3.3.1" in result["escalation_reason"]
    assert result["next_action"] == "retry"


def test_verification_rejects_unexpected_source():
    result = verify_evidence_node({
        "claim_facts": {"disruption_type": "cancellation"},
        "applicable_provisions": [
            {
                "source": "untrusted_document.pdf",
                "page": 5,
                "text": "3.3.1 Cancellation provision text",
                "clause_number": "3.3.1",
            }
        ],
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert "source" in result["escalation_reason"].lower()


def test_verification_rejects_invalid_page_metadata():
    result = verify_evidence_node({
        "claim_facts": {"disruption_type": "cancellation"},
        "applicable_provisions": [
            {
                "source": "dgca_car_revision_4.pdf",
                "page": "five",
                "text": "3.3.1 Cancellation provision text",
                "clause_number": "3.3.1",
            }
        ],
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert "metadata" in result["escalation_reason"].lower()


def test_verification_rejects_mismatched_clause_heading():
    result = verify_evidence_node({
        "claim_facts": {"disruption_type": "cancellation"},
        "applicable_provisions": [
            {
                "source": "dgca_car_revision_4.pdf",
                "page": 5,
                "text": "3.3.4 No such compensation shall be payable.",
                "clause_number": "3.3.1",
            }
        ],
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert "3.3.1" in result["escalation_reason"]


def test_verification_rejects_empty_clause_text():
    result = verify_evidence_node({
        "claim_facts": {"disruption_type": "cancellation"},
        "applicable_provisions": [
            {
                "source": "dgca_car_revision_4.pdf",
                "page": 5,
                "text": "",
                "clause_number": "3.3.1",
            }
        ],
        "retry_count": 0,
    })

    assert result["verification_status"] == "failed"
    assert "metadata" in result["escalation_reason"].lower()
