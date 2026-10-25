
import json
import math
import re
from collections import Counter
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = PROJECT_ROOT / "data" / "vector_index"
INDEX_FILE = INDEX_DIR / "corpus.faiss"
CHUNKS_FILE = INDEX_DIR / "chunks.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Initial hybrid-ranking weights. We will evaluate these rather than
# assuming they are optimal.
SEMANTIC_WEIGHT = 0.65
LEXICAL_WEIGHT = 0.35

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being",
    "by", "can", "could", "did", "do", "does", "for", "from",
    "had", "has", "have", "how", "i", "if", "in", "into", "is",
    "it", "its", "may", "must", "of", "on", "or", "our", "should",
    "that", "the", "their", "them", "there", "these", "they",
    "this", "those", "to", "under", "was", "were", "what", "when",
    "which", "who", "why", "will", "with", "would", "you", "your",
}


def tokenize(text: str) -> set[str]:
    """Extract normalized content words for lightweight lexical matching."""

    if not isinstance(text, str):
        return set()

    words = re.findall(r"[a-z][a-z0-9-]*", text.lower())

    return {
        word
        for word in words
        if len(word) > 1 and word not in STOP_WORDS
    }


class CorpusSearch:
    """Search regulatory corpus using hybrid semantic and lexical ranking."""

    def __init__(self):
        if not INDEX_FILE.exists():
            raise FileNotFoundError(
                f"Vector index not found: {INDEX_FILE}. "
                "Run scripts/build_vector_index.py first."
            )

        if not CHUNKS_FILE.exists():
            raise FileNotFoundError(
                f"Chunk metadata not found: {CHUNKS_FILE}"
            )

        self.model = SentenceTransformer(MODEL_NAME)
        self.index = faiss.read_index(str(INDEX_FILE))

        with CHUNKS_FILE.open("r", encoding="utf-8") as file:
            self.chunks = json.load(file)

        if not isinstance(self.chunks, list):
            raise ValueError("Chunk metadata must contain a JSON list.")

        if self.index.ntotal != len(self.chunks):
            raise ValueError(
                "Index and chunk metadata counts do not match."
            )

        if self.index.ntotal == 0:
            raise ValueError("Vector index is empty.")

        for position, chunk in enumerate(self.chunks):
            if not isinstance(chunk, dict):
                raise ValueError(
                    f"Chunk metadata at position {position} is not an object."
                )

            required_fields = ("chunk_id", "source", "page", "text")
            missing_fields = [
                field for field in required_fields
                if field not in chunk
            ]

            if missing_fields:
                raise ValueError(
                    f"Chunk at position {position} is missing fields: "
                    f"{', '.join(missing_fields)}"
                )

        # Prepare the lexical index once, rather than retokenizing all
        # corpus passages on every query.
        self._chunk_tokens = [
            tokenize(chunk["text"])
            for chunk in self.chunks
        ]

        document_frequency = Counter()

        for token_set in self._chunk_tokens:
            document_frequency.update(token_set)

        document_count = len(self.chunks)

        self._idf = {
            token: math.log(
                1.0
                + (
                    document_count - frequency + 0.5
                ) / (
                    frequency + 0.5
                )
            )
            for token, frequency in document_frequency.items()
        }

        # Unseen terms receive a defined IDF value too.
        self._unseen_idf = math.log(
            1.0 + (document_count + 0.5) / 0.5
        )

    def _lexical_score(
        self,
        query_tokens: set[str],
        chunk_tokens: set[str],
    ) -> float:
        """Calculate IDF-weighted query-term coverage in a passage."""

        if not query_tokens:
            return 0.0

        total_weight = sum(
            self._idf.get(token, self._unseen_idf)
            for token in query_tokens
        )

        if total_weight == 0:
            return 0.0

        matched_weight = sum(
            self._idf.get(token, self._unseen_idf)
            for token in query_tokens
            if token in chunk_tokens
        )

        return matched_weight / total_weight

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return the top passages using combined semantic and lexical scores."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or not 1 <= top_k <= 20
        ):
            raise ValueError("top_k must be between 1 and 20.")

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        query_embedding = query_embedding.astype("float32")
        query_tokens = tokenize(query)

        # Retrieve a candidate pool, then rerank it using lexical evidence.
        # For the current small corpus this includes all indexed passages.
        candidate_k = min(
            self.index.ntotal,
            max(top_k * 5, 50),
        )

        scores, indices = self.index.search(
            query_embedding,
            candidate_k,
        )

        results = []

        for score, index_position in zip(scores[0], indices[0]):
            position = int(index_position)

            if position < 0 or position >= len(self.chunks):
                continue

            semantic_score = float(score)
            lexical_score = self._lexical_score(
                query_tokens,
                self._chunk_tokens[position],
            )

            retrieval_score = (
                SEMANTIC_WEIGHT * semantic_score
                + LEXICAL_WEIGHT * lexical_score
            )

            chunk = self.chunks[position]

            results.append({
                "chunk_id": chunk["chunk_id"],
                "source": chunk["source"],
                "page": chunk["page"],
                "text": chunk["text"],
                # Original FAISS cosine similarity.
                "similarity_score": semantic_score,
                # IDF-weighted lexical coverage between 0 and 1.
                "lexical_score": lexical_score,
                # Combined score used for ranking.
                "retrieval_score": retrieval_score,
            })

        results.sort(
            key=lambda result: (
                result["retrieval_score"],
                result["similarity_score"],
            ),
            reverse=True,
        )

        return results[:top_k]
