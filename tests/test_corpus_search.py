
import json

import numpy as np
import pytest

import tools.corpus_search as corpus_search_module
from tools.corpus_search import CorpusSearch


class FakeEmbeddingModel:
    """Lightweight embedding-model substitute for unit tests."""

    def __init__(self, model_name):
        self.model_name = model_name
        self.last_texts = None
        self.last_encode_kwargs = None

    def encode(self, texts, **kwargs):
        self.last_texts = texts
        self.last_encode_kwargs = kwargs

        return np.asarray([[1.0, 0.0]], dtype=np.float32)


class FakeFaissIndex:
    """Predictable FAISS substitute for testing ranking and result handling."""

    def __init__(self):
        self.ntotal = 2

    def search(self, query_embeddings, k):
        assert query_embeddings.dtype == np.float32
        assert query_embeddings.shape == (1, 2)

        scores = np.asarray([[0.91, 0.72]], dtype=np.float32)
        indices = np.asarray([[1, 0]], dtype=np.int64)

        return scores[:, :k], indices[:, :k]


@pytest.fixture
def corpus_search(monkeypatch, tmp_path):
    """Build a CorpusSearch instance without downloading a real model."""

    index_file = tmp_path / "corpus.faiss"
    chunks_file = tmp_path / "chunks.json"

    index_file.write_bytes(b"fake-index")

    chunks = [
        {
            "chunk_id": "DGCA-3.3.1",
            "source": "dgca_car_revision_4.pdf",
            "page": 5,
            "text": "Cancellation notification provision.",
        },
        {
            "chunk_id": "DGCA-3.3.2",
            "source": "dgca_car_revision_4.pdf",
            "page": 5,
            "text": "Alternate flight and compensation provision.",
        },
    ]

    chunks_file.write_text(
        json.dumps(chunks),
        encoding="utf-8",
    )

    fake_index = FakeFaissIndex()

    monkeypatch.setattr(
        corpus_search_module,
        "INDEX_FILE",
        index_file,
    )
    monkeypatch.setattr(
        corpus_search_module,
        "CHUNKS_FILE",
        chunks_file,
    )
    monkeypatch.setattr(
        corpus_search_module,
        "SentenceTransformer",
        FakeEmbeddingModel,
    )
    monkeypatch.setattr(
        corpus_search_module.faiss,
        "read_index",
        lambda path: fake_index,
    )

    return CorpusSearch()


def test_search_returns_ranked_passages_with_citations(corpus_search):
    results = corpus_search.search(
        "What happens when a flight is cancelled?",
        top_k=5,
    )

    assert len(results) == 2

    # The original semantic ranking remains visible.
    assert results[0]["chunk_id"] == "DGCA-3.3.2"
    assert results[1]["chunk_id"] == "DGCA-3.3.1"

    assert results[0]["source"] == "dgca_car_revision_4.pdf"
    assert results[0]["page"] == 5
    assert results[0]["text"] == (
        "Alternate flight and compensation provision."
    )

    assert results[0]["similarity_score"] == pytest.approx(0.91)
    assert results[1]["similarity_score"] == pytest.approx(0.72)

    assert "lexical_score" in results[0]
    assert "retrieval_score" in results[0]

    assert corpus_search.model.last_texts == [
        "What happens when a flight is cancelled?"
    ]
    assert corpus_search.model.last_encode_kwargs[
        "normalize_embeddings"
    ] is True


def test_lexical_overlap_can_promote_a_relevant_passage(corpus_search):
    # FAISS ranks chunk 3.3.2 first, but the query directly matches
    # the cancellation and notification terms in chunk 3.3.1.
    results = corpus_search.search(
        "cancellation notification requirement",
        top_k=2,
    )

    assert results[0]["chunk_id"] == "DGCA-3.3.1"
    assert results[0]["similarity_score"] == pytest.approx(0.72)
    assert results[0]["lexical_score"] > results[1]["lexical_score"]
    assert results[0]["retrieval_score"] > results[1]["retrieval_score"]


def test_search_rejects_empty_query(corpus_search):
    with pytest.raises(ValueError, match="cannot be empty"):
        corpus_search.search("   ")


def test_search_rejects_top_k_out_of_range(corpus_search):
    with pytest.raises(ValueError, match="top_k must be between 1 and 20"):
        corpus_search.search("flight cancellation", top_k=0)
