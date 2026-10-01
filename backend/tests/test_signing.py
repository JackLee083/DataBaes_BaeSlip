import copy
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import get_config
from app.signing import (
    canonical,
    issuer_key,
    load_or_create_key,
    public_key_b64,
    public_key_from_b64,
    sign,
    verify,
)

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _body() -> dict:
    att = json.loads((FIXTURES / "verify_valid.json").read_text(encoding="utf-8"))["attestation"]
    att = copy.deepcopy(att)
    att.pop("signature", None)
    return att


def test_tamper_fails():
    key = Ed25519PrivateKey.generate()
    signed = sign(_body(), key)
    assert signed["summary"]["monthly_median"] == 2700
    signed["summary"]["monthly_median"] = 3700
    assert verify(signed, key.public_key()) is False


def test_roundtrip():
    key = Ed25519PrivateKey.generate()
    signed = sign(_body(), key)
    assert signed["signature"]["alg"] == "Ed25519"
    assert verify(signed, key.public_key()) is True


def test_sign_ignores_existing_signature():
    key = Ed25519PrivateKey.generate()
    att = _body()
    att["signature"] = {"alg": "Ed25519", "value": "AAAA"}
    assert verify(sign(att, key), key.public_key()) is True


def test_verify_with_raw_public_key():
    key = Ed25519PrivateKey.generate()
    signed = sign(_body(), key)
    pub = public_key_from_b64(public_key_b64(key))
    assert verify(signed, pub) is True


def test_canonical_sorted_compact_utf8():
    assert canonical({"b": 1, "a": "é"}) == '{"a":"é","b":1}'.encode("utf-8")


def test_fixture_signature_verifies():
    keys = json.loads((FIXTURES / "keys.json").read_text(encoding="utf-8"))["keys"]
    k1 = next(k for k in keys if k["key_id"] == "k1")
    att = json.loads((FIXTURES / "verify_valid.json").read_text(encoding="utf-8"))["attestation"]
    assert verify(att, public_key_from_b64(k1["public_key"])) is True


def test_key_created_once(tmp_path):
    path = tmp_path / "sub" / "issuer.pem"
    first = load_or_create_key(path)
    assert path.exists()
    second = load_or_create_key(path)
    assert public_key_b64(first) == public_key_b64(second)


def test_missing_or_garbled_signature_is_false():
    key = Ed25519PrivateKey.generate()
    pub = key.public_key()
    signed = sign(_body(), key)

    no_sig = {k: v for k, v in signed.items() if k != "signature"}
    assert verify(no_sig, pub) is False

    garbled = {**signed, "signature": {"alg": "Ed25519", "value": "not base64!!"}}
    assert verify(garbled, pub) is False

    other = sign(_body(), Ed25519PrivateKey.generate())
    assert verify(other, pub) is False


def test_issuer_key_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("ISSUER_KEY_PATH", str(tmp_path / "k.pem"))
    assert issuer_key(get_config()) is issuer_key(get_config())
