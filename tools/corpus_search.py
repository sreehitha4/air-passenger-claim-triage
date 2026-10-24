
import json
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = PROJECT_ROOT / "data" / "vector_index"
INDEX_FILE = INDEX_DIR / "corpus.faiss"
CHUNKS_FILE = INDEX_DIR / "chunks.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class CorpusSearch:
    """Search regulatory corpus chunks using semantic similarity."""

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

        if self.index.ntotal != len(self.chunks):
            raise ValueError(
                "Index and chunk metadata counts do not match."
            )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Return the most relevant passages for a natural-language query."""

        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20.")

        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        scores, indices = self.index.search(
            query_embedding.astype("float32"),
            min(top_k, self.index.ntotal),
        )

        results = []

        for score, index_position in zip(scores[0], indices[0]):
            if index_position < 0:
                continue

            chunk = self.chunks[int(index_position)]

            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "text": chunk["text"],
                    "similarity_score": float(score),
                }
            )

        return results
