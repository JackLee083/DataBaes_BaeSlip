import base64
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import signing
from app.config import get_config
from app.main import app
from app.models import KeysResponse

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "keys.json"
URL = "/.well-known/baeslip-keys.json"


@pytest.fixture
def pem(tmp_path, monkeypatch):
    path = tmp_path / "issuer.pem"
    monkeypatch.setenv("ISSUER_KEY_PATH", str(path))
    return path


@pytest.fixture
def client():
    return TestClient(app)


def test_published_key_verifies_a_signature(pem, client):
    att = signing.sign({"hello": "world", "n": 1}, signing.issuer_key(get_config()))
    r = client.get(URL)
    assert r.status_code == 200
    pub = signing.public_key_from_b64(r.json()["keys"][0]["public_key"])
    assert signing.verify(att, pub) is True


def test_shape_matches_fixture(pem, client):
    r = client.get(URL)
    assert r.status_code == 200
    body = r.json()
    fixture = json.loads(FIXTURE.read_text())
    assert set(body) == set(fixture) == {"keys"}
    assert set(body["keys"][0]) == set(fixture["keys"][0])
    entry = body["keys"][0]
    assert entry["key_id"] == "k1"
    assert entry["alg"] == "Ed25519"
    KeysResponse.model_validate(body)
    assert len(base64.b64decode(entry["public_key"], validate=True)) == 32


def test_key_file_created_in_tmp(pem, client):
    assert not pem.exists()
    assert client.get(URL).status_code == 200
    assert pem.exists()


def test_only_baeslip_keys_path_is_served():
    # app.routes wraps included routers lazily in this FastAPI, so read the
    # flattened route table from the OpenAPI schema instead.
    paths = sorted(p for p in app.openapi()["paths"] if p.startswith("/.well-known/"))
    assert paths == ["/.well-known/baeslip-keys.json"]


# --- scripts/sign_fixtures.py (fixtures re-signed with an in-memory key) ---

REPO = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO / "fixtures"
SCRIPT = REPO / "scripts" / "sign_fixtures.py"
ISSUER_ID = "baeslip-demo"
ISSUER_NAME = "BaeSlip Demo Issuer"
KEY_ID = "k1"
SIGNED = ("attestation.json", "verify_valid.json", "verify_revoked.json", "verify_expired.json")


def load_script():
    spec = importlib.util.spec_from_file_location("sign_fixtures_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fx(tmp_path):
    dest = tmp_path / "fixtures"
    shutil.copytree(FIXTURES_DIR, dest)
    return dest


def read(d, name):
    return json.loads((d / name).read_text(encoding="utf-8"))


def diff_paths(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
        return [p for k in a for p in diff_paths(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in diff_paths(x, y, f"{path}[{i}]")]
    return [] if a == b else [path]


def att_of(d, name):
    return read(d, name)["attestation"]


def test_resign_changes_only_issuer_and_signature(fx):
    before = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in fx.glob("*.json")}
    load_script().resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    changed = set()
    for name, old in before.items():
        for p in diff_paths(old, read(fx, name)):
            changed.add(p.removeprefix(".attestation"))
    # a re-run on already-renamed fixtures changes fewer paths, never more
    assert changed <= {".issuer.issuer_id", ".issuer.name", ".signature.value", ".keys[0].public_key"}
    assert {".signature.value", ".keys[0].public_key"} <= changed
    for name in (*SIGNED, "preview.json"):
        assert att_of(fx, name)["issuer"] == {"issuer_id": ISSUER_ID, "name": ISSUER_NAME, "key_id": KEY_ID}


def test_resign_fixtures_verify_against_new_keys(fx):
    load_script().resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    keys = {k["key_id"]: k["public_key"] for k in read(fx, "keys.json")["keys"]}
    for name in SIGNED:
        att = att_of(fx, name)
        assert signing.verify(att, signing.public_key_from_b64(keys[att["issuer"]["key_id"]])), name


def test_resign_leaves_preview_unsigned(fx):
    load_script().resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    assert "signature" not in att_of(fx, "preview.json")


def test_resign_issue_and_verify_attestations_identical(fx):
    load_script().resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    issued = att_of(fx, "attestation.json")
    assert att_of(fx, "verify_valid.json") == issued
    assert att_of(fx, "verify_revoked.json") == issued


def test_resign_twice_gives_new_signatures_and_both_verify(fx):
    module = load_script()
    module.resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    first = {n: att_of(fx, n) for n in SIGNED}
    first_pub = read(fx, "keys.json")["keys"][0]["public_key"]
    module.resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    second = {n: att_of(fx, n) for n in SIGNED}
    second_pub = read(fx, "keys.json")["keys"][0]["public_key"]
    assert first_pub != second_pub
    for n in SIGNED:
        assert first[n]["signature"]["value"] != second[n]["signature"]["value"]
        assert signing.verify(first[n], signing.public_key_from_b64(first_pub))
        assert signing.verify(second[n], signing.public_key_from_b64(second_pub))


def test_resign_never_writes_or_prints_private_key(fx, tmp_path, monkeypatch, capsys):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    known = Ed25519PrivateKey.generate()
    raw = known.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()
    )
    der = known.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    secrets = [base64.b64encode(raw).decode(), raw.hex(), base64.b64encode(der).decode(), "PRIVATE KEY"]
    module = load_script()

    class Fixed:
        @staticmethod
        def generate():
            return known

    monkeypatch.setattr(module, "Ed25519PrivateKey", Fixed)
    files_before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    module.resign(fx, ISSUER_ID, ISSUER_NAME, KEY_ID)
    out = capsys.readouterr()
    assert sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*")) == files_before
    for p in tmp_path.rglob("*"):
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            for s in secrets:
                assert s not in text, p.name
    for s in secrets:
        assert s not in out.out and s not in out.err
    assert read(fx, "keys.json")["keys"][0]["public_key"] == signing.public_key_b64(known)


def test_resign_script_never_persists_a_key():
    source = SCRIPT.read_text(encoding="utf-8")
    for banned in ("private_bytes", "load_or_create_key", "issuer_key", ".pem"):
        assert banned not in source
