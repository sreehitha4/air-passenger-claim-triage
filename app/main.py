
from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from app.models import PassengerClaim
from app.jobs import submit_job, get_job, process_job

app = FastAPI(
    title="Air Passenger Claim Triage Service",
    description=(
        "Validates passenger compensation claims and runs "
        "an evidence-grounded triage workflow. "
        "The service does not authorize payments."
    ),
    version="0.4.0",
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "air-passenger-claim-triage",
    }


@app.post("/claims/validate")
async def validate_claim(claim: PassengerClaim):
    return {
        "status": "validated",
        "claim_id": claim.claim_id,
        "message": (
            "Claim data passed validation. "
            "No compensation decision has been made."
        ),
    }


@app.post("/claims/triage")
async def triage_claim(claim: PassengerClaim):
    """Run triage immediately and return its result."""

    from agents.graph import claim_graph

    try:
        result = claim_graph.invoke({
            "claim": claim.model_dump(mode="json"),
            "retry_count": 0,
        })

        return {
            "status": "processed",
            "claim_id": result.get("claim_id", claim.claim_id),
            "next_action": result.get("next_action", "human_review"),
            "missing_information": result.get(
                "missing_information", []
            ),
            "evidence_request": result.get("evidence_request", []),
            "verification_status": result.get(
                "verification_status", "pending"
            ),
            "retrieved_passages": result.get(
                "retrieved_passages", []
            ),
            "applicable_provisions": result.get(
                "applicable_provisions", []
            ),
            "clause_assessments": result.get(
                "clause_assessments", []
            ),
            "escalation_reason": result.get("escalation_reason"),
            "recommendation": result.get("recommendation"),
            "message": (
                "Triage completed. Evidence assessments are preliminary "
                "and do not establish legal eligibility or authorize payment."
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="The claim triage workflow could not be completed.",
        ) from exc


@app.post(
    "/claims/submit",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_claim(
    claim: PassengerClaim,
    background_tasks: BackgroundTasks,
):
    """Accept a claim and process it as a background task."""

    claim_data = claim.model_dump(mode="json")
    job_id = submit_job(claim_data)

    background_tasks.add_task(
        process_job,
        job_id,
        claim_data,
    )

    return {
        "job_id": job_id,
        "claim_id": claim.claim_id,
        "status": "queued",
        "status_url": f"/jobs/{job_id}",
        "message": "Claim accepted for background processing.",
    }


@app.get("/jobs/{job_id}")
async def read_job(job_id: str):
    """Retrieve the current status and result of a submitted job."""

    job = get_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    return job
