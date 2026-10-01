"""Issue, preview, verify and revoke attestations. Owner: core (B10).

Responses omit null fields (response_model_exclude_none) so the attestation on the
wire is exactly what was signed.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app import interfaces, signing
from app.config import get_config
from app.models import (
    AttestationRequest,
    IssueResponse,
    Issuer,
    PreviewResponse,
    RevokeResponse,
    Scope,
    VerifyResponse,
)
from app.services import attestation as att_service
from app.services.store import Store, new_attestation_id, status_of

router = APIRouter(tags=["attestations"])

TZ = ZoneInfo("Australia/Melbourne")


def now() -> datetime:
    """Current time in Melbourne. Routes call it via the module so tests can patch it."""
    return datetime.now(TZ).replace(microsecond=0)


def _not_found() -> JSONResponse:
    return JSONResponse(status_code=404, content={"status": "not_found"})


def _build(body: AttestationRequest, cfg, att_id: str):
    if body.scope == Scope.lending:
        raise HTTPException(status_code=400, detail="lending scope is spec-only in the demo")
    try:
        display_name, summary = att_service.mei_summary(body.worker_id, body.scope)
    except interfaces.WorkerNotFound:
        raise HTTPException(status_code=404, detail=f"worker not found: {body.worker_id}")
    if body.period is not None and body.period != summary.period:
        raise HTTPException(status_code=400, detail="custom periods not supported in the demo")
    issuer = Issuer(issuer_id=cfg.issuer_id, name=cfg.issuer_name, key_id=cfg.key_id)
    att = att_service.build_attestation(
        display_name, summary, body.scope, now(), att_id, issuer
    )
    return display_name, att


@router.post("/attestations/preview", response_model=PreviewResponse, response_model_exclude_none=True)
def preview(body: AttestationRequest) -> PreviewResponse:
    cfg = get_config()
    display_name, att = _build(body, cfg, "preview")
    included, excluded = att_service.disclosures(body.scope, display_name)
    return PreviewResponse(included=included, excluded=excluded, attestation=att)


@router.post("/attestations", response_model=IssueResponse, response_model_exclude_none=True)
def issue(body: AttestationRequest) -> IssueResponse:
    cfg = get_config()
    att_id = new_attestation_id()
    _, att = _build(body, cfg, att_id)
    wire = att.model_dump(mode="json", exclude_none=True)
    signed = signing.sign(wire, signing.issuer_key(cfg))
    Store(cfg.store_path).save(signed)
    return {"attestation": signed, "verify_url": f"{cfg.public_web_url}/v/{att_id}"}


@router.get("/attestations/{att_id}/verify", response_model=VerifyResponse, response_model_exclude_none=True)
def verify(att_id: str):
    """Unknown id: HTTP 404 with {"status": "not_found"}."""
    cfg = get_config()
    entry = Store(cfg.store_path).get(att_id)
    if entry is None:
        return _not_found()
    return {
        "status": status_of(entry, now()),
        "signature_valid": signing.verify(entry["attestation"], signing.issuer_key(cfg).public_key()),
        "attestation": entry["attestation"],
        "revoked_at": entry.get("revoked_at"),
    }


@router.post("/attestations/{att_id}/revoke", response_model=RevokeResponse)
def revoke(att_id: str):
    cfg = get_config()
    entry = Store(cfg.store_path).revoke(att_id, now())
    if entry is None:
        return _not_found()
    return RevokeResponse(attestation_id=att_id, revoked_at=entry["revoked_at"])
