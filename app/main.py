
from fastapi import FastAPI

from app.models import PassengerClaim

app = FastAPI(
    title="Air Passenger Claim Triage Service",
    description=(
        "Validates passenger compensation claims before "
        "they enter the triage workflow."
    ),
    version="0.1.0",
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
