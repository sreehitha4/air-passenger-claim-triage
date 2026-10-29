
import re

from app.models import PassengerClaim
from agents.claim_analysis import analyze_claim
from agents.evidence_assessment import assess_provisions
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

DGCA_SOURCE = "dgca_car_revision_4.pdf"


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
        "retrieval_error": None,
        "escalation_reason": None,
    }


def research_claim_node(state: ClaimTriageState) -> dict:
    """Retrieve regulatory passages and candidate provisions safely."""

    claim_facts = state.get("claim_facts", {})
    description = claim_facts.get("description", "")
    disruption_type = claim_facts.get("disruption_type", "other")

    retry_count = state.get("retry_count", 0)
    verification_feedback = state.get("escalation_reason")

    if retry_count > 0:
        feedback = (
            verification_feedback
            or "Required clause evidence was not verified."
        )

        query = (
            f"Follow-up DGCA regulatory search for flight "
            f"{disruption_type}. "
            f"Previous verification feedback: {feedback} "
            "Find provisions that qualify, limit, exempt, or modify "
            "the initially relevant entitlement provisions. "
            "Search cross-referenced clauses, definitions, conditions, "
            "exceptions, notice periods, flight block-time categories, "
            "alternate-flight acceptance, refund arrangements, and "
            "passenger facilities including meals and refreshments. "
            "Do not infer eligibility from a compensation amount alone. "
            f"Claim details: {description}"
        )
    else:
        query = (
            f"DGCA flight {disruption_type} compensation, "
            "alternate flights, passenger facilities, "
            f"and relevant conditions. Claim details: {description}"
        )

    clauses_to_check = CLAUSES_BY_DISRUPTION.get(
        disruption_type,
        CLAUSES_BY_DISRUPTION["other"],
    )

    try:
        retrieval = RegulatoryRetrieval()
        passages = retrieval.search_corpus(query, top_k=5)

        applicable_provisions = []

        for clause_number in clauses_to_check:
            clause_results = retrieval.get_clause(clause_number)

            for clause in clause_results:
                if clause.get("source") == DGCA_SOURCE:
                    applicable_provisions.append(clause)

    except Exception as exc:
        # Keep technical details for debugging, but do not expose them
        # as the user-facing escalation reason.
        return {
            "retrieved_passages": [],
            "applicable_provisions": [],
            "clause_assessments": [],
            "retrieval_error": f"{type(exc).__name__}: {exc}",
            "verification_status": "failed",
            "next_action": "retry",
            "escalation_reason": (
                "Regulatory retrieval failed. "
                "A retry or human review is required."
            ),
        }

    return {
        "retrieved_passages": passages,
        "applicable_provisions": applicable_provisions,
        "clause_assessments": [],
        "retrieval_error": None,
        "next_action": "verify",
        "verification_status": "pending",
        "escalation_reason": None,
    }


def verify_evidence_node(state: ClaimTriageState) -> dict:
    """
    Verify clause retrieval structure and provenance.

    This does not establish legal applicability, passenger eligibility,
    or entitlement to compensation.
    """

    if state.get("retrieval_error"):
        return {
            "verification_status": "failed",
            "next_action": "retry",
            "escalation_reason": (
                "Regulatory retrieval failed. "
                "A retry or human review is required."
            ),
        }

    provisions = state.get("applicable_provisions", [])
    disruption_type = state.get("claim_facts", {}).get(
        "disruption_type",
        "other",
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

        if source != DGCA_SOURCE:
            problems.append(
                "A provision has an unexpected or missing DGCA source."
            )
            continue

        if (
            not isinstance(page, int)
            or isinstance(page, bool)
            or page < 1
            or not isinstance(text, str)
            or not text.strip()
        ):
            problems.append(
                "A retrieved provision has invalid page or text metadata."
            )
            continue

        if clause_number not in required_clauses:
            continue

        escaped_clause = re.escape(clause_number)
        heading_pattern = (
            rf"(?m)^\s*{escaped_clause}(?=\s|\(|$)"
        )

        if re.search(heading_pattern, text):
            found_clauses.add(clause_number)
        else:
            problems.append(
                f"Clause {clause_number} has no matching heading in its text."
            )

    missing_clauses = sorted(required_clauses - found_clauses)

    if missing_clauses:
        problems.append(
            "Could not verify required candidate clause headings: "
            + ", ".join(missing_clauses)
        )

    if problems:
        return {
            "verification_status": "failed",
            "next_action": "retry",
            "escalation_reason": "; ".join(dict.fromkeys(problems)),
        }

    return {
        "verification_status": "verified",
        "next_action": "complete",
        "escalation_reason": None,
    }


def assess_evidence_node(state: ClaimTriageState) -> dict:
    """Assess retrieved provisions against the available claim facts."""

    claim_facts = state.get("claim_facts", {})
    provisions = state.get("applicable_provisions", [])

    assessments = assess_provisions(claim_facts, provisions)

    return {
        "clause_assessments": assessments,
        "next_action": "complete",
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
