"""Issuer public keys, so anyone can verify a signature. Owner: core (B11)."""

from fastapi import APIRouter

from app.config import get_config
from app.models import KeysResponse, PublicKey
from app.signing import issuer_key, public_key_b64

router = APIRouter(tags=["keys"])


@router.get("/.well-known/baeslip-keys.json", response_model=KeysResponse)
def keys() -> KeysResponse:
    cfg = get_config()
    return KeysResponse(keys=[PublicKey(key_id=cfg.key_id, public_key=public_key_b64(issuer_key(cfg)))])
