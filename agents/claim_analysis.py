
from app.models import PassengerClaim


def analyze_claim(claim: PassengerClaim) -> dict:
    """
    Extract relevant facts from a validated passenger claim.

    This component organizes information for downstream agents.
    It does not decide legal entitlement.
    """

    facts = {
        "claim_id": claim.claim_id,
        "airline": claim.airline,
        "flight_number": claim.flight_number,
        "departure_airport": claim.departure_airport,
        "arrival_airport": claim.arrival_airport,
        "disruption_type": claim.disruption_type.value,
        "scheduled_departure": claim.scheduled_departure.isoformat(),
        "notification_time": (
            claim.notification_time.isoformat()
            if claim.notification_time
            else None
        ),
        "actual_departure": (
            claim.actual_departure.isoformat()
            if claim.actual_departure
            else None
        ),
        "alternate_flight_taken": claim.alternate_flight_taken,
        "alternate_flight_delay_hours": (
            claim.alternate_flight_delay_hours
        ),
        "description": claim.description,
        "evidence_references": claim.evidence_references,
    }

    missing_information = []

    if claim.notification_time is None:
        missing_information.append("notification_time")

    if (
        claim.disruption_type.value == "cancellation"
        and claim.alternate_flight_taken
        and claim.alternate_flight_delay_hours is None
    ):
        missing_information.append("alternate_flight_delay_hours")

    return {
        "claim_id": claim.claim_id,
        "claim_facts": facts,
        "missing_information": missing_information,
        "requires_regulatory_research": True,
        "legal_conclusion": None,
    }
