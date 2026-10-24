
from typing import Any, Literal, TypedDict


class ClaimTriageState(TypedDict, total=False):
    # Input
    claim: dict[str, Any]
    claim_id: str
    evidence_request: list[str]

    # Agent 1: claim analysis
    claim_facts: dict[str, Any]
    missing_information: list[str]

    # Agent 2: regulatory research
    retrieved_passages: list[dict[str, Any]]
    applicable_provisions: list[dict[str, Any]]
    clause_assessments: list[dict[str, Any]]
    verification_status: Literal[
        "pending",
        "verified",
        "failed",
        "insufficient_evidence",
    ]

    # Workflow control
    retry_count: int
    next_action: Literal[
        "research",
        "verify",
        "retry",
        "request_evidence",
        "human_review",
        "complete",
    ]

    # Final output
    recommendation: dict[str, Any] | None
    escalation_reason: str | None
