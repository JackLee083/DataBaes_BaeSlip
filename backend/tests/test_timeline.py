import json
from pathlib import Path

from app.models import TimelineResponse
from app.services.loader import load_worker
from app.services.summary import build_timeline

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def test_mei_timeline_equals_fixture():
    expected = TimelineResponse.model_validate(json.loads((FIXTURES / "timeline.json").read_text()))
    assert build_timeline(load_worker("mei")) == expected


def test_months_cover_period_even_if_empty():
    w = load_worker("mei")
    keep = [i for i in w.income if i.paid_on.strftime("%Y-%m") != "2026-06"]
    assert len(keep) < len(w.income)
    t = build_timeline(w.model_copy(update={"income": keep}))
    assert list(t.months) == [f"2026-0{m}" for m in range(4, 10)]
    assert t.months["2026-06"].net_cents == 0
    assert t.months["2026-06"].self_reported_cents == 0


def test_d_counted_as_self_reported_only():
    t = build_timeline(load_worker("mei"))
    assert t.months["2026-08"].self_reported_cents == 6000
    assert t.months["2026-08"].net_cents == 262000
