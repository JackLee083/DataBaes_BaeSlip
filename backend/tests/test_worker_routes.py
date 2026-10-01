"""Tests for routers/worker.py (data-8). Everything is monkeypatched; no network."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import interfaces
from app.main import app
from app.models import Check, ChecksResponse, TimelineResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"

client = TestClient(app)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_timeline_calls_interfaces(monkeypatch):
    sentinel = object()
    seen = {}
    expected = TimelineResponse.model_validate(_fixture("timeline.json"))

    def fake_load(worker_id):
        seen["id"] = worker_id
        return sentinel

    def fake_build(worker):
        seen["worker"] = worker
        return expected

    monkeypatch.setattr(interfaces, "load_worker", fake_load)
    monkeypatch.setattr(interfaces, "build_timeline", fake_build)

    r = client.get("/workers/w1/timeline")
    assert r.status_code == 200
    assert seen == {"id": "w1", "worker": sentinel}
    assert (
        TimelineResponse.model_validate(r.json()).model_dump(mode="json")
        == expected.model_dump(mode="json")
    )


def test_checks_uses_run_all_checks(monkeypatch):
    fixture = ChecksResponse.model_validate(_fixture("checks.json"))
    sentinel = object()
    seen = {}

    def fake_run(worker, cfg=None):
        seen["worker"] = worker
        return [Check.model_validate(c.model_dump()) for c in fixture.checks]

    monkeypatch.setattr(interfaces, "load_worker", lambda worker_id: sentinel)
    monkeypatch.setattr(interfaces, "run_all_checks", fake_run)

    r = client.get("/workers/w1/checks")
    assert r.status_code == 200
    assert seen["worker"] is sentinel
    assert (
        ChecksResponse.model_validate(r.json()).model_dump(mode="json")
        == fixture.model_dump(mode="json")
    )


@pytest.mark.parametrize("path", ["timeline", "checks"])
def test_unknown_worker_404(monkeypatch, path):
    def fake_load(worker_id):
        raise interfaces.WorkerNotFound(worker_id)

    monkeypatch.setattr(interfaces, "load_worker", fake_load)
    r = client.get(f"/workers/nope/{path}")
    assert r.status_code == 404
