
from copy import deepcopy
from threading import Lock
from uuid import uuid4

from agents.graph import claim_graph


_jobs: dict[str, dict] = {}
_jobs_lock = Lock()


def submit_job(claim: dict) -> str:
    """Create a job record and return its unique ID."""
    job_id = str(uuid4())

    with _jobs_lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "claim_id": claim["claim_id"],
            "status": "queued",
            "result": None,
            "error": None,
        }

    return job_id


def get_job(job_id: str) -> dict | None:
    """Return a copy of a job record."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        return deepcopy(job) if job is not None else None


def process_job(job_id: str, claim: dict) -> None:
    """Run claim triage and store its result."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["status"] = "running"

    try:
        result = claim_graph.invoke({
            "claim": claim,
            "retry_count": 0,
        })

        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is not None:
                job["status"] = "completed"
                job["result"] = result

    except Exception:
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is not None:
                job["status"] = "failed"
                job["error"] = (
                    "The claim triage workflow could not be completed."
                )
