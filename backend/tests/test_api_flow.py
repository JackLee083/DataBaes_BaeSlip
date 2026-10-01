"""End-to-end API flow: preview, issue, verify, revoke. Uses the fixture fallback for Mei."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main, models, signing
from app.routers import attestations as att_router

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
client = TestClient(main.app)
BODY = {"worker_id": "mei", "scope": "rental"}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("STORE_PATH", str(tmp_path / "att.json"))
    monkeypatch.setenv("ISSUER_KEY_PATH", str(tmp_path / "k.pem"))
    monkeypatch.setenv("PUBLIC_WEB_URL", "http://phone.test:5173")


def fx(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def issue() -> dict:
    r = client.post("/attestations", json=BODY)
    assert r.status_code == 200, r.text
    return r.json()


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


def test_issue_verify_revoke():
    body = issue()
    att_id = body["attestation"]["attestation_id"]
    assert body["verify_url"] == f"http://phone.test:5173/v/{att_id}"

    v = client.get(f"/attestations/{att_id}/verify")
    assert v.status_code == 200
    j = v.json()
    assert j["status"] == "valid"
    assert j["signature_valid"] is True
    assert j["attestation"]["summary"]["monthly_median"] == 2700
    assert "revoked_at" not in j

    r = client.post(f"/attestations/{att_id}/revoke")
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"
    assert r.json()["revoked_at"]

    j = client.get(f"/attestations/{att_id}/verify").json()
    assert j["status"] == "revoked"
    assert j["revoked_at"]
    assert j["signature_valid"] is True


def test_unknown_is_404_not_found():
    for resp in (
        client.get("/attestations/att_nope/verify"),
        client.post("/attestations/att_nope/revoke"),
    ):
        assert resp.status_code == 404
        assert resp.json() == {"status": "not_found"}


def test_unknown_worker_404():
    assert client.post("/attestations", json={"worker_id": "bob"}).status_code == 404


def test_preview_is_unsigned_and_lists_exclusions():
    r = client.post("/attestations/preview", json=BODY)
    assert r.status_code == 200
    att = r.json()["attestation"]
    assert "signature" not in att
    assert att["attestation_id"] == "preview"
    assert r.json()["excluded"]


def test_preview_excluded_lists_forbidden_concepts():
    excluded = client.post("/attestations/preview", json=BODY).json()["excluded"]
    keys = {d["key"] for d in excluded}
    assert {"hours", "visa", "transactions", "checks"} <= keys


def test_lending_rejected_400():
    r = client.post("/attestations", json={"worker_id": "mei", "scope": "lending"})
    assert r.status_code == 400
    assert "detail" in r.json()
    r = client.post("/attestations/preview", json={"worker_id": "mei", "scope": "lending"})
    assert r.status_code == 400


def test_custom_period_rejected_400():
    period = {"start": "2026-05-01", "end": "2026-06-30"}
    r = client.post("/attestations", json={**BODY, "period": period})
    assert r.status_code == 400


def test_expired_after_30_days(monkeypatch):
    att = issue()["attestation"]
    later = datetime.fromisoformat(att["issued_at"]) + timedelta(days=31)
    monkeypatch.setattr(att_router, "now", lambda: later)
    j = client.get(f"/attestations/{att['attestation_id']}/verify").json()
    assert j["status"] == "expired"


def test_wire_json_verifies_with_published_key():
    att_id = issue()["attestation"]["attestation_id"]
    wire = client.get(f"/attestations/{att_id}/verify").json()["attestation"]

    keys = client.get("/.well-known/baeslip-keys.json")
    assert keys.status_code == 200
    pub = signing.public_key_from_b64(keys.json()["keys"][0]["public_key"])
    assert signing.verify(wire, pub) is True

    tampered = json.loads(json.dumps(wire))
    assert tampered["summary"]["monthly_median"] == 2700
    tampered["summary"]["monthly_median"] = 3700
    assert signing.verify(tampered, pub) is False


def test_responses_match_fixture_shapes():
    issued = issue()
    att_id = issued["attestation"]["attestation_id"]
    fx_issue = fx("attestation.json")
    assert set(issued) == set(fx_issue)
    assert set(issued["attestation"]) == set(fx_issue["attestation"])

    valid = client.get(f"/attestations/{att_id}/verify").json()
    fx_valid = fx("verify_valid.json")
    assert set(valid) == set(fx_valid)
    assert set(valid["attestation"]) == set(fx_valid["attestation"])

    revoke = client.post(f"/attestations/{att_id}/revoke").json()
    assert set(revoke) == set(fx("revoke.json"))

    revoked = client.get(f"/attestations/{att_id}/verify").json()
    fx_revoked = fx("verify_revoked.json")
    assert set(revoked) == set(fx_revoked)
    assert set(revoked["attestation"]) == set(fx_revoked["attestation"])


def test_no_forbidden_keys_in_nested_attestation():
    preview = client.post("/attestations/preview", json=BODY).json()["attestation"]
    issued = issue()
    att = issued["attestation"]
    verified = client.get(f"/attestations/{att['attestation_id']}/verify").json()["attestation"]
    for a in (preview, att, verified):
        assert not set(walk_keys(a)) & models.FORBIDDEN_ATTESTATION_KEYS


def test_issuer_and_api_title_are_baeslip():
    att = issue()["attestation"]
    assert att["issuer"] == {
        "issuer_id": "baeslip-demo",
        "name": "BaeSlip Demo Issuer",
        "key_id": "k1",
    }
    assert client.get("/openapi.json").json()["info"]["title"] == "BaeSlip Issuer API"
