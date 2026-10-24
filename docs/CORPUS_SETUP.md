# Corpus Setup Guide

## 1. Purpose

The corpus provides the source documents used by the Air Passenger Compensation Claim Triage Service to retrieve regulatory and airline-policy passages.

The current corpus configuration uses:

- DGCA Civil Aviation Requirements (CAR), Section 3, Series M, Part IV, Revision 4
- IndiGo Conditions of Carriage

## 2. Source Documents

The source PDFs are maintained locally and are not included in the Git repository.

Before using the pipeline, obtain the relevant documents from their official sources and save them in the `corpus/` directory using these exact filenames:

- `dgca_car_revision_4.pdf`
- `indigo_conditions_of_carriage.pdf`

Check the documents' publication details, version, and redistribution permissions before sharing copies publicly.

## 3. Environment Setup

Create and activate a Python virtual environment from the project root.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Build the Corpus

Run the scripts from the project root, in this order.

### Step 1: Extract PDF text

```powershell
python scripts/ingest_corpus.py
```

Output:

`data/extracted_corpus.json`

The extraction process stores text with source filenames and page numbers.

### Step 2: Create text chunks

```powershell
python scripts/chunk_corpus.py
```

Output:

`data/corpus_chunks.json`

The current chunking configuration targets 1,600 characters per chunk with approximately 200 characters of overlap.

### Step 3: Build the vector index

```powershell
python scripts/build_vector_index.py
```

Outputs:

- `data/vector_index/corpus.faiss`
- `data/vector_index/chunks.json`

The current embedding model is `sentence-transformers/all-MiniLM-L6-v2`. The first run may need to download the model.

## 5. Verify Retrieval

Run:

```powershell
python -m scripts.test_retrieval
python -m scripts.test_corpus_search
```

Review the retrieved source, page number, clause text, and relevance to the query. Retrieval similarity alone does not establish that a provision legally applies to a claim.

## 6. Run Tests

```powershell
python -m pytest -v
```

The current automated test suite has 24 tests. Re-run the suite after making changes and review any failures.

## 7. Generated Files

The extracted corpus, chunks, and vector index are generated locally. Rebuild them using the commands above rather than relying on generated artifacts being present in a fresh clone.

## 8. Limitations

- The quality of retrieval depends on PDF text extraction and chunk boundaries.
- Retrieved provisions require claim-specific applicability checks.
- Source-document versions should be checked periodically.
- The system supports claim triage and evidence gathering; it does not independently authorize compensation payments.
