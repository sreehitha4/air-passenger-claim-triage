
from tools.corpus_search import CorpusSearch


def main():
    searcher = CorpusSearch()

    query = (
        "For a cancelled flight, when must the airline provide "
        "compensation and free meals or refreshments while "
        "passengers wait for an alternate flight?"
    )

    results = searcher.search(query, top_k=5)

    print(f"\nQuery: {query}")
    print(f"Results returned: {len(results)}")

    for rank, result in enumerate(results, start=1):
        print(f"\n--- Result {rank} ---")
        print(f"Source: {result['source']}")
        print(f"Page: {result['page']}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Similarity: {result['similarity_score']:.4f}")
        print(f"Text:\n{result['text'][:700]}")


if __name__ == "__main__":
    main()
