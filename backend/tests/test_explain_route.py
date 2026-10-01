"""POST /checks/{check_id}/explain route. Offline: interfaces are monkeypatched."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import interfaces
from app.main import app
from app.models import Check, ExplainResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
CHECK_ID = "r1-abc-cafe-2026-09-01"


def _checks() -> list[Check]:
    data = json.loads((FIXTURES / "checks.json").read_text(encoding="utf-8"))
    return [Check.model_validate(c) for c in data["checks"]]


def _explain() -> ExplainResponse:
    data = json.loads((FIXTURES / "explain.json").read_text(encoding="utf-8"))
    return ExplainResponse.model_validate(data)


@pytest.fixture
def calls(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    record: list[tuple[Check, str]] = []

    def fake_explain(check, language):
        record.append((check, language))
        return _explain()

    monkeypatch.setattr(interfaces, "load_worker", lambda worker_id: object())
    monkeypatch.setattr(interfaces, "run_all_checks", lambda worker, cfg=None: _checks())
    monkeypatch.setattr(interfaces, "explain_check", fake_explain)
    return record


client = TestClient(app)


def test_explain_known_check_offline(calls):
    r = client.post(f"/checks/{CHECK_ID}/explain", json={"language": "en"})
    assert r.status_code == 200
    assert r.json() == json.loads((FIXTURES / "explain.json").read_text(encoding="utf-8"))


def test_default_language_is_en(calls):
    assert client.post(f"/checks/{CHECK_ID}/explain", json={}).status_code == 200
    assert calls[0][1] == "en"


def test_requested_language_forwarded(calls):
    assert client.post(f"/checks/{CHECK_ID}/explain", json={"language": "en"}).status_code == 200
    assert calls[0][1] == "en"


def test_only_selected_check_forwarded(calls):
    client.post(f"/checks/{CHECK_ID}/explain", json={})
    assert len(calls) == 1
    check = calls[0][0]
    assert check.check_id == CHECK_ID
    assert check == next(c for c in _checks() if c.check_id == CHECK_ID)


def test_response_shape(calls):
    r = client.post(f"/checks/{CHECK_ID}/explain", json={})
    assert set(r.json()) == {"text", "source"}


def test_unknown_check_id_404(calls):
    r = client.post("/checks/nope/explain", json={})
    assert r.status_code == 404
    assert calls == []


def test_worker_not_found_404(monkeypatch, calls):
    def boom(worker_id):
        raise interfaces.WorkerNotFound(worker_id)

    monkeypatch.setattr(interfaces, "load_worker", boom)
    assert client.post(f"/checks/{CHECK_ID}/explain", json={}).status_code == 404
    assert calls == []


def test_invalid_body_422(calls):
    assert client.post(f"/checks/{CHECK_ID}/explain", json={"language": 5}).status_code == 422
    assert calls == []
