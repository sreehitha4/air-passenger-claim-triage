
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_FILE = PROJECT_ROOT / "data" / "extracted_corpus.json"


def lookup_clause(clause_number: str) -> list[dict]:
    """
    Find actual numbered clause headings in the extracted corpus.

    Excludes common subparagraph references such as '3.8.1 (a)'
    when looking for the heading of clause '3.8.1'.
    """
    clause_number = clause_number.strip()

    if not re.fullmatch(r"\d+(?:\.\d+){1,3}", clause_number):
        raise ValueError(
            "Provide a clause number such as '3.3.2' or '3.8.1'."
        )

    if not CORPUS_FILE.exists():
        raise FileNotFoundError(
            f"Extracted corpus not found: {CORPUS_FILE}"
        )

    with CORPUS_FILE.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    # Match a numbered clause at the beginning of a line.
    heading_pattern = re.compile(
        rf"(?m)^[ \t]*{re.escape(clause_number)}[ \t]+"
        rf"(?!\([a-z]\))"
    )

    # Detect the start of another numbered clause.
    next_heading_pattern = re.compile(
        r"(?m)^[ \t]*\d+(?:\.\d+){1,3}[ \t]+"
    )

    matches = []

    for page in pages:
        text = page["text"]

        for match in heading_pattern.finditer(text):
            start = match.start()
            remaining_text = text[match.end():]

            next_heading = next_heading_pattern.search(remaining_text)

            end = (
                match.end() + next_heading.start()
                if next_heading
                else min(len(text), start + 1800)
            )

            matches.append({
                "clause_number": clause_number,
                "source": page["source"],
                "page": page["page"],
                "text": text[start:end].strip(),
            })

    return matches
