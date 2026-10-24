
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "corpus_chunks.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "vector_index"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Chunk file not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        chunks = json.load(file)

    if not chunks:
        raise ValueError("No corpus chunks found.")

    texts = [chunk["text"] for chunk in chunks]

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(OUTPUT_DIR / "corpus.faiss"))

    with (OUTPUT_DIR / "chunks.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(chunks, file, ensure_ascii=False, indent=2)

    print(f"\nChunks indexed: {index.ntotal}")
    print(f"Embedding dimensions: {embeddings.shape[1]}")
    print(f"Saved vector index to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
