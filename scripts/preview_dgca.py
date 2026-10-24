
import json
from pathlib import Path

corpus_file = Path("data/extracted_corpus.json")

with corpus_file.open("r", encoding="utf-8") as file:
    pages = json.load(file)

for page in pages:
    if page["source"] == "dgca_car_revision_4.pdf":
        preview = page["text"][:250].replace("\n", " ")
        print(f'Page {page["page"]}: {preview}')
        print("-" * 60)
