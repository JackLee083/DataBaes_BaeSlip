"""data-9: end-to-end over the real data modules (no monkeypatching)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import interfaces
from app.main import app
from app.models import Scope, TimelineResponse

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
client = TestClient(app)


def test_timeline_route_equals_fixture():
    r = client.get("/workers/mei/timeline")
    assert r.status_code == 200
    want = TimelineResponse.model_validate(json.loads((FIXTURES / "timeline.json").read_text()))
    assert TimelineResponse.model_validate(r.json()) == want


def test_unknown_404():
    assert client.get("/workers/nobody/timeline").status_code == 404
    assert client.get("/workers/nobody/checks").status_code == 404


def test_interfaces_summary_mei():
    s = interfaces.summarize_worker(interfaces.load_worker("mei"), Scope.rental).summary
    assert (s.monthly_income_range.low, s.monthly_income_range.high) == (2300, 3100)
    assert s.monthly_median == 2700
    assert (s.coverage.months_with_data, s.coverage.months_in_period) == (6, 6)
