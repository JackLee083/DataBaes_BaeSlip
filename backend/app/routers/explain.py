"""POST /checks/{check_id}/explain. Owner: rules (B13)."""

from fastapi import APIRouter, HTTPException

from app import interfaces
from app.models import ExplainRequest, ExplainResponse

router = APIRouter(tags=["explain"])

# Single-worker demo: checks are always looked up for this worker.
DEMO_WORKER_ID = "mei"


@router.post("/checks/{check_id}/explain", response_model=ExplainResponse)
def explain_check(check_id: str, body: ExplainRequest) -> ExplainResponse:
    try:
        worker = interfaces.load_worker(DEMO_WORKER_ID)
    except interfaces.WorkerNotFound:
        raise HTTPException(status_code=404, detail="worker not found") from None
    checks = interfaces.run_all_checks(worker)
    check = next((c for c in checks if c.check_id == check_id), None)
    if check is None:
        raise HTTPException(status_code=404, detail=f"check not found: {check_id}")
    return interfaces.explain_check(check, body.language)
