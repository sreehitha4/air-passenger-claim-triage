
import json
from pathlib import Path

from pypdf import PdfReader


# Locate the project root and input/output folders.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = PROJECT_ROOT / "corpus"
OUTPUT_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = OUTPUT_DIR / "extracted_corpus.json"

PDF_FILES = [
    "dgca_car_revision_4.pdf",
    "indigo_conditions_of_carriage.pdf",
]



def clean_extracted_text(text: str) -> str:
    """Normalize whitespace and repair confirmed PDF extraction artefacts."""

    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        # Repair only the extraction errors confirmed in the DGCA PDF.
        line = line.replace("a ffected", "affected")
        line = line.replace("t he", "the")

        if line:
            lines.append(line)

    return "\n".join(lines)



def extract_pdf_text(pdf_path: Path) -> list[dict]:
    """Extract PDF text page by page while retaining source information."""

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        text = clean_extracted_text(raw_text)

        if text.strip():
            extracted_pages.append(
                {
                    "source": pdf_path.name,
                    "page": page_number,
                    "text": text,
                }
            )

    if not extracted_pages:
        raise ValueError(
            f"No extractable text found in {pdf_path.name}"
        )

    return extracted_pages


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_pages = []

    for filename in PDF_FILES:
        pdf_path = CORPUS_DIR / filename
        pages = extract_pdf_text(pdf_path)
        all_pages.extend(pages)

        print(f"Extracted {len(pages)} pages from {filename}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            all_pages,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nTotal pages extracted: {len(all_pages)}")
    print(f"Saved extracted text to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
