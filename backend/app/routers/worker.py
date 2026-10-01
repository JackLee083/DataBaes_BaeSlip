"""Worker-only routes: timeline and integrity checks. Owner: data (B12)."""

from fastapi import APIRouter, HTTPException

from app import interfaces
from app.models import ChecksResponse, TimelineResponse

router = APIRouter(tags=["worker"])


def _load(worker_id: str):
    try:
        return interfaces.load_worker(worker_id)
    except interfaces.WorkerNotFound:
        raise HTTPException(status_code=404, detail="worker not found")


@router.get("/workers/{worker_id}/timeline", response_model=TimelineResponse)
def timeline(worker_id: str) -> TimelineResponse:
    """interfaces.build_timeline(interfaces.load_worker(worker_id)); unknown id -> 404."""
    return interfaces.build_timeline(_load(worker_id))


@router.get("/workers/{worker_id}/checks", response_model=ChecksResponse)
def checks(worker_id: str) -> ChecksResponse:
    """interfaces.run_all_checks(interfaces.load_worker(worker_id)); worker only."""
    return ChecksResponse(checks=interfaces.run_all_checks(_load(worker_id)))
