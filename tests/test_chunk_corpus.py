
from scripts.chunk_corpus import build_dgca_blocks, make_dgca_chunks


def test_dgca_clause_continuation_is_preserved_across_pages():
    pages = [
        {
            "source": "dgca_car_revision_4.pdf",
            "page": 4,
            "text": (
                "CIVIL AVIATION REQUIREMENTS\n"
                "4\n"
                "3.2.3 A passenger on connecting flights shall be "
                "compensated under Para 3.2.2 of this CAR,"
            ),
        },
        {
            "source": "dgca_car_revision_4.pdf",
            "page": 5,
            "text": (
                "CIVIL AVIATION REQUIREMENTS\n"
                "5\n"
                "when the passenger arrives at the final destination "
                "at least three hours later than scheduled.\n"
                "3.3 Cancellation of Flight\n"
                "3.3.1 The airline shall inform the passenger."
            ),
        },
    ]

    chunks = make_dgca_chunks(
        "dgca_car_revision_4.pdf",
        pages,
    )

    clause = next(
        chunk for chunk in chunks
        if chunk["clause_number"] == "3.2.3"
    )

    assert clause["pages"] == [4, 5]
    assert clause["page"] == 4
    assert "connecting flights" in clause["text"]
    assert "three hours later" in clause["text"]


def test_dgca_numbered_clauses_have_separate_chunks():
    pages = [
        {
            "page": 4,
            "text": (
                "3.2 Denied Boarding\n"
                "3.2.1 The airline must first ask for volunteers.\n"
                "3.2.2 Compensation depends on alternate-flight timing."
            ),
        },
    ]

    chunks = make_dgca_chunks(
        "dgca_car_revision_4.pdf",
        pages,
    )

    clause_numbers = [
        chunk["clause_number"]
        for chunk in chunks
    ]

    assert "3.2.1" in clause_numbers
    assert "3.2.2" in clause_numbers

    clause_321 = next(
        chunk for chunk in chunks
        if chunk["clause_number"] == "3.2.1"
    )
    clause_322 = next(
        chunk for chunk in chunks
        if chunk["clause_number"] == "3.2.2"
    )

    assert "volunteers" in clause_321["text"]
    assert "alternate-flight timing" in clause_322["text"]


def test_cross_page_clause_chunk_keeps_source_and_start_page():
    pages = [
        {
            "page": 5,
            "text": (
                "3.3.4 Compensation shall not be payable in "
                "extraordinary circumstances beyond the"
            ),
        },
        {
            "page": 6,
            "text": (
                "control of the airline even if reasonable measures "
                "were taken.\n"
                "3.3.5 Refunds shall follow the applicable requirements."
            ),
        },
    ]

    blocks = build_dgca_blocks(pages)

    clause_block = next(
        block for block in blocks
        if block["text"].startswith("3.3.4")
    )

    assert clause_block["start_page"] == 5
    assert clause_block["pages"] == [5, 6]
    assert "control of the airline" in clause_block["text"]
