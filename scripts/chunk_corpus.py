
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "extracted_corpus.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "corpus_chunks.json"

CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200


def split_text(text: str) -> list[str]:
    """Split text near paragraph boundaries, with overlapping context."""

    paragraphs = [
        paragraph.strip()
        for paragraph in text.split("\n")
        if paragraph.strip()
    ]

    chunks = []
    current_parts = []
    current_length = 0

    for paragraph in paragraphs:
        # Keep a long paragraph intact where possible; split it only
        # when it would make the current chunk too large.
        if len(paragraph) > CHUNK_SIZE:
            if current_parts:
                chunks.append("\n".join(current_parts))
                current_parts = []
                current_length = 0

            start = 0
            while start < len(paragraph):
                end = min(start + CHUNK_SIZE, len(paragraph))
                piece = paragraph[start:end].strip()

                if piece:
                    chunks.append(piece)

                if end == len(paragraph):
                    break

                start = end - CHUNK_OVERLAP

            continue

        extra_length = len(paragraph) + (1 if current_parts else 0)

        if current_parts and current_length + extra_length > CHUNK_SIZE:
            previous_text = "\n".join(current_parts)
            chunks.append(previous_text)

            # Carry the tail of the previous chunk into the next one
            # to preserve context around chunk boundaries.
            overlap = previous_text[-CHUNK_OVERLAP:].strip()
            current_parts = [overlap, paragraph] if overlap else [paragraph]
            current_length = sum(len(part) for part in current_parts)
        else:
            current_parts.append(paragraph)
            current_length += extra_length

    if current_parts:
        chunks.append("\n".join(current_parts))

    return [chunk for chunk in chunks if chunk.strip()]


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Extracted corpus not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    all_chunks = []

    for page in pages:
        text_chunks = split_text(page["text"])

        for index, chunk_text in enumerate(text_chunks, start=1):
            all_chunks.append(
                {
                    "chunk_id": (
                        f"{Path(page['source']).stem}"
                        f"_p{page['page']}_c{index}"
                    ),
                    "source": page["source"],
                    "page": page["page"],
                    "text": chunk_text,
                }
            )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            all_chunks,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Input pages: {len(pages)}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Target chunk size: {CHUNK_SIZE} characters")
    print(f"Chunk overlap: approximately {CHUNK_OVERLAP} characters")
    print(f"Saved chunks to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
