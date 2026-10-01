"""Issuer key, canonical JSON, Ed25519 sign and verify."""

import base64
import binascii
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

_KEY_CACHE: dict[Path, Ed25519PrivateKey] = {}


def canonical(obj: dict) -> bytes:
    """Keys sorted, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_or_create_key(path: Path) -> Ed25519PrivateKey:
    path = Path(path)
    if path.exists():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError(f"{path} is not an Ed25519 private key")
        return key
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key


def sign(att: dict, key: Ed25519PrivateKey) -> dict:
    """Sign everything except `signature`; returns the attestation with a signature."""
    body = {k: v for k, v in att.items() if k != "signature"}
    sig = key.sign(canonical(body))
    return {**body, "signature": {"alg": "Ed25519", "value": base64.b64encode(sig).decode("ascii")}}


def verify(att: dict, pub: Ed25519PublicKey) -> bool:
    try:
        body = {k: v for k, v in att.items() if k != "signature"}
        sig = base64.b64decode(att["signature"]["value"], validate=True)
        pub.verify(sig, canonical(body))
        return True
    except (InvalidSignature, KeyError, ValueError, TypeError, binascii.Error):
        return False


def public_key_b64(key: Ed25519PrivateKey) -> str:
    """Base64 of the raw 32-byte public key."""
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return base64.b64encode(raw).decode("ascii")


def public_key_from_b64(b64: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(b64))


def issuer_key(cfg) -> Ed25519PrivateKey:
    """Issuer key for cfg.issuer_key_path, cached per resolved path."""
    path = Path(cfg.issuer_key_path).resolve()
    if path not in _KEY_CACHE:
        _KEY_CACHE[path] = load_or_create_key(path)
    return _KEY_CACHE[path]
