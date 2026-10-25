
import json
from pathlib import Path
from statistics import mean
from typing import Any

from tools.corpus_search import CorpusSearch


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALUATION_FILE = PROJECT_ROOT / "evaluation" / "retrieval_eval.json"
RESULTS_FILE = PROJECT_ROOT / "evaluation" / "retrieval_eval_results.json"


def load_evaluation(path: Path) -> tuple[int, list[dict[str, Any]]]:
    """Load and validate the labelled retrieval evaluation dataset."""

    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    queries = data.get("queries")
    top_k = data.get("top_k", 5)

    if not isinstance(queries, list) or not queries:
        raise ValueError("Evaluation dataset must contain a non-empty queries list.")

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer.")

    seen_ids = set()

    for item in queries:
        if not isinstance(item, dict):
            raise ValueError("Each evaluation query must be a JSON object.")

        query_id = item.get("id")
        query = item.get("query")
        relevant_ids = item.get("relevant_chunk_ids")

        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError("Every evaluation query must have a non-empty id.")

        if query_id in seen_ids:
            raise ValueError(f"Duplicate evaluation query ID: {query_id}")
        seen_ids.add(query_id)

        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"{query_id}: query text cannot be empty.")

        if (
            not isinstance(relevant_ids, list)
            or not relevant_ids
            or not all(isinstance(value, str) and value for value in relevant_ids)
        ):
            raise ValueError(
                f"{query_id}: relevant_chunk_ids must be a non-empty list of strings."
            )

    return top_k, queries


def evaluate_retrieval(
    searcher: CorpusSearch,
    queries: list[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    """Calculate per-query Recall@K and reciprocal rank, then aggregate."""

    per_query = []

    for item in queries:
        query_id = item["id"]
        query_text = item["query"]
        relevant_ids = set(item["relevant_chunk_ids"])

        retrieved = searcher.search(query_text, top_k=top_k)
        ranked_ids = [result["chunk_id"] for result in retrieved[:top_k]]

        matched_ids = [
            chunk_id for chunk_id in ranked_ids
            if chunk_id in relevant_ids
        ]

        recall_at_k = len(set(matched_ids)) / len(relevant_ids)

        first_relevant_rank = next(
            (
                rank
                for rank, chunk_id in enumerate(ranked_ids, start=1)
                if chunk_id in relevant_ids
            ),
            None,
        )

        reciprocal_rank = (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        )

        per_query.append({
            "id": query_id,
            "topic": item.get("topic", "unspecified"),
            "query": query_text,
            "relevant_chunk_ids": sorted(relevant_ids),
            "retrieved_chunk_ids": ranked_ids,
            "matched_relevant_chunk_ids": matched_ids,
            "recall_at_k": recall_at_k,
            "first_relevant_rank": first_relevant_rank,
            "reciprocal_rank": reciprocal_rank,
        })

    return {
        "evaluation_file": str(EVALUATION_FILE.relative_to(PROJECT_ROOT)),
        "query_count": len(per_query),
        "k": top_k,
        "recall_at_k": mean(
            row["recall_at_k"] for row in per_query
        ),
        "mrr": mean(
            row["reciprocal_rank"] for row in per_query
        ),
        "per_query": per_query,
    }


def main() -> None:
    top_k, queries = load_evaluation(EVALUATION_FILE)

    print(f"Evaluation queries: {len(queries)}")
    print(f"Retrieval cutoff: {top_k}")
    print("Loading the existing search index and embedding model...")

    searcher = CorpusSearch()
    report = evaluate_retrieval(searcher, queries, top_k)

    print("\nPer-query results")
    print("-" * 90)

    for row in report["per_query"]:
        rank = row["first_relevant_rank"]
        status = f"rank {rank}" if rank is not None else "NO RELEVANT RESULT IN TOP-K"

        print(
            f'{row["id"]} | '
            f'Recall@{top_k}={row["recall_at_k"]:.3f} | '
            f'MRR={row["reciprocal_rank"]:.3f} | '
            f'{status}'
        )

    print("\nAggregate metrics")
    print("-" * 40)
    print(f'Queries evaluated: {report["query_count"]}')
    print(f'Recall@{top_k}: {report["recall_at_k"]:.4f}')
    print(f'Mean Reciprocal Rank (MRR): {report["mrr"]:.4f}')

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(f"\nDetailed report saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
