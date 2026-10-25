
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "extracted_corpus.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "corpus_chunks.json"

CHUNK_SIZE = 1600
CHUNK_OVERLAP = 200

DGCA_SOURCE_STEM = "dgca_car_revision_4"

CLAUSE_HEADING_PATTERN = re.compile(
    r"^\s*(?P<clause>\d{1,2}(?:\.\d{1,2}){1,2})[ \t]+(?=[A-Z])"
)

DGCA_RUNNING_HEADERS = {
    "civil aviation requirements",
    "series ‘m’ part iv",
    "series 'm' part iv",
    "section 3",
    "6th august, 2010",
}


def extract_clause_number(text: str) -> str | None:
    """Return the numbered clause heading when one starts the text."""

    match = CLAUSE_HEADING_PATTERN.match(text)
    return match.group("clause") if match else None


def clean_dgca_line(line: str) -> bool:
    """Return True for recurring DGCA page headers and page numbers."""

    normalized = re.sub(r"\s+", " ", line.strip()).lower()

    if not normalized:
        return True

    if normalized in DGCA_RUNNING_HEADERS:
        return True

    if re.fullmatch(r"\d{1,2}", normalized):
        return True

    if re.fullmatch(
        r"rev\.\s*4,\s*dated\s+25th\s+jan,\s*2023",
        normalized,
        flags=re.IGNORECASE,
    ):
        return True

    return False


def split_long_block(text: str) -> list[str]:
    """Split an oversized block near sentence boundaries."""

    text = text.strip()

    if not text:
        return []

    if len(text) <= CHUNK_SIZE:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) > CHUNK_SIZE:
            if current:
                chunks.append(current)
                current = ""

            start = 0

            while start < len(sentence):
                end = min(start + CHUNK_SIZE, len(sentence))
                piece = sentence[start:end].strip()

                if piece:
                    chunks.append(piece)

                if end == len(sentence):
                    break

                start = end - CHUNK_OVERLAP

            continue

        candidate = f"{current} {sentence}".strip()

        if current and len(candidate) > CHUNK_SIZE:
            chunks.append(current)
            current = sentence
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def split_text(text: str) -> list[str]:
    """Split text into numbered clause blocks within a single page."""

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    blocks = []
    current_lines = []

    for line in lines:
        is_heading = CLAUSE_HEADING_PATTERN.match(line) is not None

        if is_heading and current_lines:
            blocks.append(" ".join(current_lines))
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        blocks.append(" ".join(current_lines))

    chunks = []

    for block in blocks:
        chunks.extend(split_long_block(block))

    return [chunk for chunk in chunks if chunk.strip()]


def build_dgca_blocks(
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build blocks across consecutive DGCA pages.

    A numbered clause remains open until the next numbered clause begins,
    including when its text continues onto the following PDF page.
    """

    blocks = []
    current_lines: list[str] = []
    current_start_page: int | None = None
    current_pages: set[int] = set()

    def finish_block() -> None:
        nonlocal current_lines, current_start_page, current_pages

        if current_lines and current_start_page is not None:
            blocks.append({
                "start_page": current_start_page,
                "pages": sorted(current_pages),
                "text": " ".join(current_lines).strip(),
            })

        current_lines = []
        current_start_page = None
        current_pages = set()

    for page in sorted(pages, key=lambda item: int(item["page"])):
        page_number = int(page["page"])
        text = page["text"]

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line or clean_dgca_line(line):
                continue

            is_heading = (
                CLAUSE_HEADING_PATTERN.match(line) is not None
            )

            if is_heading and current_lines:
                finish_block()

            if current_start_page is None:
                current_start_page = page_number

            current_lines.append(line)
            current_pages.add(page_number)

    finish_block()

    return blocks


def make_dgca_chunks(
    source: str,
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create DGCA chunks with clause-based IDs and page provenance."""

    stem = Path(source).stem
    blocks = build_dgca_blocks(pages)

    chunks = []
    unnumbered_counters: dict[int, int] = defaultdict(int)

    for block in blocks:
        text_parts = split_long_block(block["text"])
        clause_number = extract_clause_number(block["text"])
        start_page = block["start_page"]

        for part_number, part_text in enumerate(text_parts, start=1):
            if clause_number:
                clause_slug = clause_number.replace(".", "_")

                if len(text_parts) == 1:
                    chunk_id = f"{stem}_clause_{clause_slug}"
                else:
                    chunk_id = (
                        f"{stem}_clause_{clause_slug}_part{part_number}"
                    )
            else:
                unnumbered_counters[start_page] += 1
                chunk_id = (
                    f"{stem}_p{start_page}_c"
                    f"{unnumbered_counters[start_page]}"
                )

            chunks.append({
                "chunk_id": chunk_id,
                "source": source,
                "page": start_page,
                "pages": block["pages"],
                "clause_number": clause_number,
                "text": part_text,
            })

    return chunks


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Extracted corpus not found: {INPUT_FILE}"
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    if not isinstance(pages, list):
        raise ValueError(
            "Extracted corpus must contain a JSON list of page records."
        )

    pages_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for page in pages:
        if not isinstance(page, dict):
            raise ValueError(
                "Each extracted page must be a JSON object."
            )

        missing = [
            field for field in ("source", "page", "text")
            if field not in page
        ]

        if missing:
            raise ValueError(
                "Extracted page is missing fields: "
                + ", ".join(missing)
            )

        if not isinstance(page["text"], str):
            raise ValueError("Page text must be a string.")

        try:
            int(page["page"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid page number: {page['page']}"
            ) from exc

        pages_by_source[page["source"]].append(page)

    all_chunks = []

    for source, source_pages in pages_by_source.items():
        if Path(source).stem == DGCA_SOURCE_STEM:
            all_chunks.extend(
                make_dgca_chunks(source, source_pages)
            )
        else:
            # Keep other documents page-scoped because their structure
            # may not use the same numbered-clause format.
            per_page_counters: dict[int, int] = defaultdict(int)

            for page in sorted(
                source_pages,
                key=lambda item: int(item["page"]),
            ):
                page_number = int(page["page"])
                text_chunks = split_text(page["text"])

                for chunk_text in text_chunks:
                    per_page_counters[page_number] += 1
                    clause_number = extract_clause_number(chunk_text)

                    all_chunks.append({
                        "chunk_id": (
                            f"{Path(source).stem}_p{page_number}_c"
                            f"{per_page_counters[page_number]}"
                        ),
                        "source": source,
                        "page": page_number,
                        "pages": [page_number],
                        "clause_number": clause_number,
                        "text": chunk_text,
                    })

    if not all_chunks:
        raise ValueError(
            "No chunks were created. Check the extracted corpus."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            all_chunks,
            file,
            ensure_ascii=False,
            indent=2,
        )

    spanning_chunks = [
        chunk for chunk in all_chunks
        if len(chunk["pages"]) > 1
    ]

    print(f"Input pages: {len(pages)}")
    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Chunks spanning multiple pages: {len(spanning_chunks)}")
    print("Chunking strategy: clause-aware with cross-page continuation")
    print(f"Saved chunks to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
