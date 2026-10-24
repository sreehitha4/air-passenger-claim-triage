
import re

from app.models import PassengerClaim
from agents.claim_analysis import analyze_claim
from agents.state import ClaimTriageState
from tools.retrieval import RegulatoryRetrieval


# Candidate clauses to investigate for each disruption type.
# These are retrieval targets, not proof of eligibility.

CLAUSES_BY_DISRUPTION = {
    "cancellation": [
        "3.3.1",
        "3.3.2",
        "3.3.3",
        "3.3.4",
        "3.3.5",
        "3.8.1",
    ],
    "delay": [
        "3.4.1",
        "3.4.2",
        "3.4.3",
        "3.4.4",
        "3.4.5",
        "3.8.1",
    ],
    "denied_boarding": [
        "3.2.1",
        "3.2.2",
        "3.2.3",
        "3.8.1",
    ],
    "downgrading": [
        "3.5.1",
    ],
    "other": [
        "3.9.1",
        "3.9.2",
        "3.9.3",
    ],
}


def analyze_claim_node(state: ClaimTriageState) -> dict:
    """Analyze a validated claim and identify missing information."""

    claim = PassengerClaim.model_validate(state["claim"])
    analysis = analyze_claim(claim)

    next_action = (
        "request_evidence"
        if analysis["missing_information"]
        else "research"
    )

    return {
        "claim_id": analysis["claim_id"],
        "claim_facts": analysis["claim_facts"],
        "missing_information": analysis["missing_information"],
        "next_action": next_action,
        "retry_count": state.get("retry_count", 0),
        "verification_status": "pending",
    }


def research_claim_node(state: ClaimTriageState) -> dict:
    """Retrieve relevant passages and candidate regulatory provisions."""

    claim_facts = state.get("claim_facts", {})
    description = claim_facts.get("description", "")
    disruption_type = claim_facts.get("disruption_type", "other")

    query = (
        f"DGCA flight {disruption_type} compensation, "
        "alternate flights, passenger facilities, "
        f"and relevant conditions. Claim details: {description}"
    )

    retrieval = RegulatoryRetrieval()
    passages = retrieval.search_corpus(query, top_k=5)

    clauses_to_check = CLAUSES_BY_DISRUPTION.get(
        disruption_type,
        CLAUSES_BY_DISRUPTION["other"],
    )

    applicable_provisions = []

    for clause_number in clauses_to_check:
        clause_results = retrieval.get_clause(clause_number)

        for clause in clause_results:
            if clause.get("source") == "dgca_car_revision_4.pdf":
                applicable_provisions.append(clause)

    return {
        "retrieved_passages": passages,
        "applicable_provisions": applicable_provisions,
        "next_action": "verify",
        "verification_status": "pending",
    }


def verify_evidence_node(state: ClaimTriageState) -> dict:
    """
    Check required clause headings and source metadata.

    This verifies retrieval structure, not legal applicability
    or passenger eligibility.
    """

    provisions = state.get("applicable_provisions", [])

    disruption_type = state.get("claim_facts", {}).get(
        "disruption_type", "other"
    )

    required_clauses = set(
        CLAUSES_BY_DISRUPTION.get(
            disruption_type,
            CLAUSES_BY_DISRUPTION["other"],
        )
    )

    found_clauses = set()
    problems = []

    for provision in provisions:
        source = provision.get("source")
        page = provision.get("page")
        text = provision.get("text", "")
        clause_number = provision.get("clause_number", "")

        if (
            not source
            or not isinstance(page, int)
            or not text.strip()
        ):
            problems.append(
                "A retrieved provision has incomplete source metadata."
            )
            continue

        escaped_clause = re.escape(clause_number)
        heading_pattern = (
            rf"(?m)^\s*{escaped_clause}\s+(?=\S)"
        )

        if (
            clause_number in required_clauses
            and re.search(heading_pattern, text)
        ):
            found_clauses.add(clause_number)

    missing_clauses = sorted(required_clauses - found_clauses)

    if missing_clauses:
        problems.append(
            "Could not verify clause headings: "
            + ", ".join(missing_clauses)
        )

    if problems:
        return {
            "verification_status": "failed",
            "next_action": "human_review",
            "escalation_reason": "; ".join(problems),
        }

    return {
        "verification_status": "verified",
        "next_action": "complete",
        "escalation_reason": None,
    }

def request_evidence_node(state: ClaimTriageState) -> dict:
    """Prepare an explicit request for missing claim information."""
    missing_information = state.get("missing_information", [])

    field_prompts = {
        "notification_time": (
            "Please provide when the airline informed you of the cancellation."
        ),
        "alternate_flight_delay_hours": (
            "Please provide the delay between the original and alternate flight."
        ),
        "actual_departure": (
            "Please provide the actual departure date and time, if known."
        ),
    }

    questions = [
        field_prompts.get(
            field,
            f"Please provide the missing information: {field}.",
        )
        for field in missing_information
    ]

    return {
        "next_action": "request_evidence",
        "evidence_request": questions,
    }

