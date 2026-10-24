from agents.evidence_assessment import assess_clause_evidence


def make_provision(
    clause_number="3.3.1",
    source="dgca_car_revision_4.pdf",
    page=5,
    text="3.3.1 Cancellation provision text.",
):
    return {
        "clause_number": clause_number,
        "source": source,
        "page": page,
        "text": text,
    }


def test_assessment_preserves_clause_citation():
    facts = {
        "disruption_type": "cancellation",
        "notification_time": "2026-10-24T14:00:00",
        "alternate_flight_taken": False,
        "alternate_flight_delay_hours": None,
    }

    result = assess_clause_evidence(facts, make_provision())

    assert result["clause_number"] == "3.3.1"
    assert result["source"] == "dgca_car_revision_4.pdf"
    assert result["page"] == 5
    assert result["assessment_status"] == "requires_condition_review"
    assert result["legal_conclusion"] is None


def test_assessment_flags_missing_notification_time():
    facts = {
        "disruption_type": "cancellation",
        "notification_time": None,
        "alternate_flight_taken": False,
        "alternate_flight_delay_hours": None,
    }

    result = assess_clause_evidence(facts, make_provision())

    assert result["assessment_status"] == "insufficient_evidence"
    assert any(
        "notification time" in gap.lower()
        for gap in result["evidence_gaps"]
    )


def test_assessment_flags_missing_alternate_flight_delay():
    facts = {
        "disruption_type": "cancellation",
        "notification_time": "2026-10-24T14:00:00",
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": None,
    }

    provision = make_provision(
        clause_number="3.3.2",
        text="3.3.2 Alternate-flight provision text.",
    )

    result = assess_clause_evidence(facts, provision)

    assert result["assessment_status"] == "insufficient_evidence"
    assert any(
        "alternate-flight delay" in gap.lower()
        for gap in result["evidence_gaps"]
    )


def test_assessment_does_not_make_legal_conclusion():
    facts = {"disruption_type": "other"}

    result = assess_clause_evidence(
        facts,
        make_provision(
            clause_number="3.9.1",
            page=8,
            text="3.9.1 Other provision text.",
        ),
    )

    assert result["legal_conclusion"] is None


def test_assessment_lists_conditions_for_clause_332():
    facts = {
        "disruption_type": "cancellation",
        "notification_time": "2026-10-24T14:00:00",
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": 4,
        "scheduled_departure": "2026-10-24T15:30:00",
        "evidence_references": [],
    }

    result = assess_clause_evidence(
        facts,
        make_provision(
            clause_number="3.3.2",
            text="3.3.2 Passenger cancellation provision requiring review.",
        ),
    )

    assert result["assessment_status"] == "requires_condition_review"
    assert result["conditions_to_review"]
    assert any(
        "block-time" in condition.lower()
        for condition in result["conditions_to_review"]
    )
    assert result["legal_conclusion"] is None


def test_conditions_are_not_marked_verified_automatically():
    facts = {
        "disruption_type": "cancellation",
        "notification_time": "2026-10-24T14:00:00",
        "alternate_flight_taken": True,
        "alternate_flight_delay_hours": 4,
        "scheduled_departure": "2026-10-24T15:30:00",
        "evidence_references": [],
    }

    result = assess_clause_evidence(
        facts,
        make_provision(
            clause_number="3.3.2",
            text="3.3.2 Cancellation provision requiring review.",
        ),
    )

    assert result["condition_review_status"] == "not_assessed"
    assert result["conditions_to_review"]
    assert result["legal_conclusion"] is None


def test_assessment_flags_invalid_citation_metadata():
    facts = {"disruption_type": "other"}

    provision = make_provision(
        clause_number="3.9.1",
        source="",
        page=0,
        text="",
    )

    result = assess_clause_evidence(facts, provision)

    assert result["assessment_status"] == "insufficient_evidence"
    assert any(
        "source document" in gap.lower()
        for gap in result["evidence_gaps"]
    )
    assert any(
        "source page" in gap.lower()
        for gap in result["evidence_gaps"]
    )
    assert any(
        "clause text" in gap.lower()
        for gap in result["evidence_gaps"]
    )
    assert result["legal_conclusion"] is None


def test_assessment_flags_clause_number_text_mismatch():
    facts = {"disruption_type": "other"}

    provision = make_provision(
        clause_number="3.3.2",
        source="dgca_car_revision_4.pdf",
        page=5,
        text="3.3.1 Cancellation provision text.",
    )

    result = assess_clause_evidence(facts, provision)

    assert result["assessment_status"] == "insufficient_evidence"
    assert any(
        "does not match" in gap.lower()
        for gap in result["evidence_gaps"]
    )
    assert result["legal_conclusion"] is None


def test_clause_heading_does_not_match_a_longer_clause_number():
    facts = {"disruption_type": "other"}

    provision = make_provision(
        clause_number="3.3.1",
        text="3.3.10 A different clause provision.",
    )

    result = assess_clause_evidence(facts, provision)

    assert result["assessment_status"] == "insufficient_evidence"
    assert any(
        "does not match" in gap.lower()
        for gap in result["evidence_gaps"]
    )