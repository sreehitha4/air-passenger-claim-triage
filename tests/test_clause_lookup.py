
import pytest

from tools.clause_lookup import lookup_clause


def test_lookup_finds_cancellation_clause():
    results = lookup_clause("3.3.2")

    dgca_results = [
        result
        for result in results
        if result["source"] == "dgca_car_revision_4.pdf"
    ]

    assert len(dgca_results) == 1
    assert dgca_results[0]["page"] == 5
    assert "3.3.2" in dgca_results[0]["text"]


def test_lookup_finds_actual_facilities_heading():
    results = lookup_clause("3.8.1")

    dgca_results = [
        result
        for result in results
        if result["source"] == "dgca_car_revision_4.pdf"
    ]

    # The actual clause heading is on page 7.
    assert len(dgca_results) == 1
    assert dgca_results[0]["page"] == 7
    assert dgca_results[0]["text"].startswith("3.8.1")


def test_lookup_finds_delay_clause():
    results = lookup_clause("3.4.1")

    dgca_results = [
        result
        for result in results
        if result["source"] == "dgca_car_revision_4.pdf"
    ]

    assert len(dgca_results) == 1
    assert dgca_results[0]["page"] == 6
    assert "3.4.1" in dgca_results[0]["text"]


def test_lookup_rejects_invalid_clause_number():
    with pytest.raises(ValueError):
        lookup_clause("invalid-clause")


def test_lookup_rejects_empty_clause_number():
    with pytest.raises(ValueError):
        lookup_clause("")
