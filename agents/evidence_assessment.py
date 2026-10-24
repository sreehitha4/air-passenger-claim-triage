import re
from typing import Any


# These are review prompts, not automatic interpretations of the law.
# The retrieved clause text remains the source for human verification.

CONDITIONS_TO_REVIEW = {
    "3.3.1": [
        "Verify the cancellation-notice timeline against the clause.",
        "Verify whether an alternate flight or refund was offered.",
    ],
    "3.3.2": [
        "Verify whether the passenger was informed as required by clause 3.3.1.",
        "Check whether a connecting flight booked under the same ticket number was missed.",
        "Verify the original flight's block-time category and the applicable compensation calculation.",
        "Check whether an alternate flight acceptable to the passenger was provided, or whether compensation in addition to a full refund was provided, as applicable.",
        "If the passenger had already reported for the original flight and waited for an alternate, review the facilities requirement referenced in clause 3.8.1(a).",
    ],
    "3.3.3": [
        "Verify whether adequate passenger contact information was provided.",
        "Check the applicable refund or alternate-travel arrangements.",
    ],
    "3.3.4": [
        "Check whether extraordinary circumstances are asserted and supported.",
        "Verify the relevant circumstances against the source provisions.",
    ],
    "3.3.5": [
        "Verify the applicable refund requirements against the source text.",
    ],
    "3.4.1": [
        "Verify the applicable delay threshold and passenger circumstances.",
        "Check the relevant meal and refreshment requirements.",
    ],
    "3.8.1": [
        "Verify the applicable passenger-facility conditions and waiting period.",
    ],
}


def _citation_heading_matches(
    clause_number: str,
    clause_text: str,
) -> bool:
    """
    Check whether clause_text starts with the declared clause heading.

    This verifies consistency between citation metadata and the retrieved
    text. It does not verify the legal meaning or applicability of the clause.
    """

    heading_pattern = (
        rf"^\s*{re.escape(clause_number.strip())}(?=\s|\(|$)"
    )

    return re.match(heading_pattern, clause_text) is not None


def assess_clause_evidence(
    claim_facts: dict[str, Any],
    provision: dict[str, Any],
) -> dict[str, Any]:
    """
    Record available claim facts, evidence gaps, and conditions
    requiring further review.

    Citation metadata and its heading are checked for basic consistency.
    This function does not establish legal applicability or
    compensation entitlement.
    """

    clause_number = provision.get("clause_number")
    source = provision.get("source")
    page = provision.get("page")
    clause_text = provision.get("text", "")

    evidence_gaps: list[str] = []
    supporting_facts: dict[str, Any] = {}

    # Validate citation metadata.
    if not isinstance(clause_number, str) or not clause_number.strip():
        evidence_gaps.append("Missing clause number.")

    if not isinstance(source, str) or not source.strip():
        evidence_gaps.append("Missing source document.")

    if (
        not isinstance(page, int)
        or isinstance(page, bool)
        or page < 1
    ):
        evidence_gaps.append("Missing or invalid source page.")

    if not isinstance(clause_text, str) or not clause_text.strip():
        evidence_gaps.append("Missing clause text.")

    # Ensure the citation's declared clause number agrees with the
    # heading at the beginning of the retrieved text.
    if (
        isinstance(clause_number, str)
        and clause_number.strip()
        and isinstance(clause_text, str)
        and clause_text.strip()
        and not _citation_heading_matches(clause_number, clause_text)
    ):
        evidence_gaps.append(
            "Clause number in citation metadata does not match "
            "the heading at the start of the clause text."
        )

    disruption_type = claim_facts.get("disruption_type")

    # Record relevant facts without treating them as proof of eligibility.
    if disruption_type == "cancellation":
        fields = [
            "notification_time",
            "scheduled_departure",
            "alternate_flight_taken",
            "alternate_flight_delay_hours",
            "evidence_references",
        ]

        for field in fields:
            supporting_facts[field] = claim_facts.get(field)

        if claim_facts.get("notification_time") is None:
            evidence_gaps.append(
                "Cancellation notification time has not been provided."
            )

        if (
            claim_facts.get("alternate_flight_taken") is True
            and claim_facts.get("alternate_flight_delay_hours") is None
        ):
            evidence_gaps.append(
                "Alternate-flight delay has not been provided."
            )

    elif disruption_type == "delay":
        fields = [
            "scheduled_departure",
            "actual_departure",
            "evidence_references",
        ]

        for field in fields:
            supporting_facts[field] = claim_facts.get(field)

        if claim_facts.get("actual_departure") is None:
            evidence_gaps.append(
                "Actual departure time has not been provided."
            )

    else:
        supporting_facts["disruption_type"] = disruption_type
        supporting_facts["evidence_references"] = (
            claim_facts.get("evidence_references")
        )

    # These checks are review prompts, not a determination that a
    # condition applies or that the passenger has met it.
    conditions_to_review = CONDITIONS_TO_REVIEW.get(
        clause_number,
        [
            "Review the retrieved clause text and identify its "
            "conditions before assessing applicability."
        ],
    )

    if evidence_gaps:
        assessment_status = "insufficient_evidence"
    else:
        assessment_status = "requires_condition_review"

    return {
        "clause_number": clause_number,
        "source": source,
        "page": page,
        "clause_text": clause_text,
        "assessment_status": assessment_status,
        "supporting_facts": supporting_facts,
        "evidence_gaps": list(dict.fromkeys(evidence_gaps)),
        "conditions_to_review": conditions_to_review,
        "condition_review_status": "not_assessed",
        "legal_conclusion": None,
    }


def assess_provisions(
    claim_facts: dict[str, Any],
    provisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assess each retrieved provision independently."""

    return [
        assess_clause_evidence(claim_facts, provision)
        for provision in provisions
    ]