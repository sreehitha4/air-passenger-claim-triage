
from tools.retrieval import RegulatoryRetrieval
from agents.nodes import CLAUSES_BY_DISRUPTION


def main():
    retrieval = RegulatoryRetrieval()

    print("=== TEST 1: SEMANTIC SEARCH ===")
    results = retrieval.search_corpus(
        "DGCA cancellation compensation and alternate flight",
        top_k=3,
    )

    print("Results found:", len(results))

    for result in results:
        print(
            f"\nSource: {result['source']}"
            f"\nPage: {result['page']}"
            f"\nSimilarity: {result['similarity_score']:.4f}"
            f"\nText: {result['text'][:300]}"
        )

    print("\n=== TEST 2: EXACT CLAUSE LOOKUP ===")
    clauses = retrieval.get_clause("3.3.2")

    print("Matches found:", len(clauses))

    for clause in clauses:
        print(f"\nSource: {clause['source']}")
        print(f"Page: {clause['page']}")
        print(f"Text:\n{clause['text'][:700]}")

    print("\n=== TEST 3: DISRUPTION CLAUSE LOOKUP ===")

    for disruption, clause_numbers in CLAUSES_BY_DISRUPTION.items():
        print(f"\nDisruption: {disruption}")

        for clause_number in clause_numbers:
            matches = retrieval.get_clause(clause_number)

            dgca_matches = [
                match
                for match in matches
                if match.get("source") == "dgca_car_revision_4.pdf"
            ]

            print(
                f"  Clause {clause_number}: "
                f"{len(dgca_matches)} DGCA match(es)"
            )

            for match in dgca_matches:
                preview = match["text"][:140].replace("\n", " ")
                print(f"    Page {match['page']}: {preview}")


if __name__ == "__main__":
    main()
