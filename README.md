# Air Passenger Claim Triage

An evidence-grounded, multi-agent MLOps service for triaging air passenger compensation claims using DGCA regulations and airline conditions of carriage.

The system validates claim information, retrieves relevant regulatory passages, verifies evidence metadata, identifies missing information, and routes claims through an agent-based workflow. It supports preliminary evidence assessment and human review; it does **not** determine final legal eligibility or authorize compensation payments.

## Project Overview

Air passenger claims involving cancellations, delays, denied boarding, and downgrading can require reviewing multiple regulatory provisions and supporting documents. This project explores how an automated, evidence-grounded workflow can help organize that process while preserving traceability and escalating cases that require further review.

### Key Features

- **Claim validation:** Validate claim fields and reject invalid or unexpected input.
- **Multi-agent workflow:** Coordinate claim analysis, regulatory research, evidence verification, and evidence assessment.
- **Hybrid retrieval:** Combine semantic similarity and lexical matching to retrieve relevant regulatory passages.
- **Clause lookup:** Locate numbered clauses in extracted regulatory documents.
- **Evidence verification:** Check source provenance, page metadata, clause headings, and required candidate provisions.
- **Retry handling:** Use verification feedback to guide targeted follow-up retrieval.
- **Missing-information requests:** Identify missing claim details and generate follow-up questions.
- **Background processing:** Submit claims as jobs and retrieve their processing status and results.
- **Automated evaluation:** Run tests and scenario-based evaluations to assess workflow behavior.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| FastAPI | REST API |
| Uvicorn | ASGI server |
| LangGraph | Agent workflow orchestration |
| LangChain and LangChain Community | Supporting language-model and retrieval integrations |
| Sentence Transformers | Semantic text embeddings |
| FAISS CPU | Vector similarity search |
| Pydantic | Request and data validation |
| PyPDF | PDF text extraction |
| Pytest | Automated testing |
| HTTPX | HTTP client and API testing support |

## Architecture

The service follows a modular workflow:

1. **API layer** — receives claim submissions and validates requests.
2. **Claim analysis** — extracts claim facts and identifies missing information.
3. **Regulatory retrieval** — searches extracted documents for relevant passages and candidate clauses.
4. **Evidence verification** — checks the structure and provenance of retrieved evidence.
5. **Evidence assessment** — compares available evidence with claim facts without making a final legal determination.
6. **Workflow routing** — requests missing information, retries unsuccessful verification, completes processing, or escalates cases for human review.
7. **Evaluation and monitoring** — provides automated checks and supporting project infrastructure.

### Workflow at a glance

```text
Claim Submission
       |
       v
Validation and Claim Analysis
       |
       +---- Missing information ----> Request Evidence
       |
       v
Regulatory Retrieval
       |
       v
Evidence Verification
       |
       +---- Verification failure ---> Targeted Retry
       |                                  |
       |                                  v
       |                           Human Review if needed
       |
       v
Evidence Assessment
       |
       v
Preliminary Triage Result
```

## Repository Structure

```text
air-passenger-claim-triage/
├── agents/          # Agent nodes, state, graph, and claim workflow
├── app/             # FastAPI application and data models
├── corpus/          # Regulatory and airline source documents
├── data/            # Extracted regulatory corpus data
├── docs/            # Project documentation
├── evaluation/      # Evaluation scenarios and reports
├── monitoring/      # Monitoring-related project components
├── scripts/         # Evaluation and utility scripts
├── tests/           # Automated test suite
├── tools/           # Retrieval, clause lookup, and supporting tools
├── .gitignore
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 recommended
- Git
- A virtual environment
- Access to the source documents and extracted corpus required by the retrieval pipeline

The commands below use PowerShell on Windows.

### 1. Clone the repository

```powershell
git clone https://github.com/sreehitha4/air-passenger-claim-triage.git
cd air-passenger-claim-triage
```

### 2. Create and activate a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, use the Python executable inside `.venv` directly or adjust your PowerShell execution policy according to your environment's security requirements.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The semantic retrieval components may download pretrained embedding-model files when first initialized. Initial startup can therefore take longer than subsequent runs.

### 4. Check the corpus files

Confirm that the required regulatory documents and extracted corpus data are available in the expected locations. The clause lookup implementation reads:

```text
data/extracted_corpus.json
```

The retrieval pipeline also depends on the source documents and corpus configuration used by the project. Ensure those assets are available before running the full workflow.

### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload
```

The service should be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check service health |
| `POST` | `/claims/validate` | Validate a claim |
| `POST` | `/claims/triage` | Run the triage workflow immediately |
| `POST` | `/claims/submit` | Submit a claim for background processing |
| `GET` | `/jobs/{job_id}` | Retrieve a submitted job's status and result |

### Example: Health Check

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Example: Validate a Claim

Send a JSON request to `POST /claims/validate`:

```json
{
  "claim_id": "CLAIM-DEMO-001",
  "passenger_name": "Test Passenger",
  "airline": "Example Airways",
  "flight_number": "EA101",
  "departure_airport": "BLR",
  "arrival_airport": "DEL",
  "scheduled_departure": "2026-11-01T10:00:00+05:30",
  "disruption_type": "cancellation",
  "notification_time": "2026-11-01T08:30:00+05:30",
  "actual_departure": null,
  "alternate_flight_taken": true,
  "alternate_flight_delay_hours": 4,
  "description": "Flight cancelled before departure.",
  "evidence_references": []
}
```

The example is synthetic and intended for testing only. Use the exact fields and constraints defined by `app/models.py`.

### Synchronous and Asynchronous Processing

- `POST /claims/triage` runs the workflow and returns a triage result in the response.
- `POST /claims/submit` accepts a claim and returns HTTP `202 Accepted` with a job ID and status URL.
- `GET /jobs/{job_id}` returns the current job state, including its result or a safe error message when processing fails.

Background job states include `queued`, `running`, `completed`, and `failed`.

## Running Tests

Activate the virtual environment and run these commands from the project root.

### Full test suite

On Windows PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q
```

### API tests

```powershell
pytest tests/test_api.py -q
```

### Agent node tests

```powershell
pytest tests/test_agent_nodes.py -q
```

The test suite covers API validation, agent behavior, retry handling, clause lookup, corpus search, evidence assessment, and other workflow components.

## Running the Evaluation

Run the scenario-based evaluation script:

```powershell
python scripts/evaluate_claim_triage.py
```

The script reports the number of scenarios evaluated, passed, and failed, along with the pass rate. The detailed report is written to:

```text
evaluation/claim_triage_eval_results.json
```

Evaluation results describe performance against the configured scenarios; they do not establish legal correctness or guarantee real-world claim outcomes.

## Evidence Traceability and Responsible Use

The system checks retrieved evidence for structural consistency and expected source metadata. Depending on the retrieval path, evidence records may contain source filenames, page numbers, clause identifiers, and supporting text.

Important safeguards include:

- Missing or malformed evidence can trigger verification failure and another retrieval attempt.
- Repeated verification failures can lead to human review.
- Claim descriptions are treated as data rather than trusted instructions.
- Candidate clause retrieval does not establish that a provision legally applies to a passenger.
- A successful test or evaluation result is not proof of regulatory completeness.

The service is an engineering prototype for evidence-grounded triage. Regulatory interpretation, eligibility determinations, and compensation decisions require appropriate human review.

## Limitations

- Retrieval quality depends on the completeness and accuracy of the available source documents and extracted text.
- Scenario-based evaluation covers only the cases represented in the evaluation dataset.
- Background job state is maintained in application memory; it is not a durable distributed job queue.
- Performance and model initialization depend on the execution environment.
- The service does not authorize payments or replace legal advice or official airline and regulatory processes.

## Future Improvements

Potential improvements, subject to project scope, include persistent job storage, stronger corpus versioning, more comprehensive evaluation datasets, and richer operational monitoring.
