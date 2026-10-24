
from tools.corpus_search import CorpusSearch
from tools.clause_lookup import lookup_clause


class RegulatoryRetrieval:
    """Unified interface for semantic search and exact clause lookup."""

    def __init__(self):
        self.corpus_search = CorpusSearch()

    def search_corpus(self, query: str, top_k: int = 5) -> list[dict]:
        """Find relevant passages using semantic similarity."""
        return self.corpus_search.search(query, top_k=top_k)

    def get_clause(self, clause_number: str) -> list[dict]:
        """Retrieve a specific numbered clause from the source corpus."""
        return lookup_clause(clause_number)
