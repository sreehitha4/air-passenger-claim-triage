
import json
import re
from pathlib import Path

corpus_file = Path("data/extracted_corpus.json")

with corpus_file.open("r", encoding="utf-8") as file:
    pages = json.load(file)

pattern = re.compile(r"\b(3\.\d+(?:\.\d+)?)\s+([^\n]{0,120})")
seen = set()

for page in pages:
    if page["source"] != "dgca_car_revision_4.pdf":
        continue

    for match in pattern.finditer(page["text"]):
        clause_number = match.group(1)
        heading_text = match.group(2).strip()

        key = (clause_number, heading_text)
        if key in seen:
            continue

        seen.add(key)
        print(
            f'Page {page["page"]} | '
            f'{clause_number} | {heading_text}'
        )
