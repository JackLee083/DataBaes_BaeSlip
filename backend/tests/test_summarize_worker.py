import json
from pathlib import Path

from app.models import Scope
from app.services.loader import load_worker
from app.services.summary import summarize_worker

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())["attestation"]


def mei(scope):
    return summarize_worker(load_worker("mei"), scope)


def test_mei_rental_equals_preview_fixture():
    s = mei(Scope.rental)
    dumped = s.summary.model_dump(mode="json")
    assert dumped == fixture("preview.json")["summary"]
    assert dumped == fixture("attestation.json")["summary"]
    assert (s.summary.monthly_income_range.low, s.summary.monthly_income_range.high) == (2300, 3100)
    assert s.summary.monthly_median == 2700
    assert (s.summary.coverage.months_with_data, s.summary.coverage.months_in_period) == (6, 6)
    got = [{"label": x.label, "type": x.type.value, "tier": x.tier.value, "evidence": [e.value for e in x.evidence]} for x in s.sources]
    assert got == fixture("preview.json")["sources"] == fixture("attestation.json")["sources"]


def test_d_source_dropped():
    s = mei(Scope.rental)
    assert "cash-tutoring" not in [x.source_id for x in s.sources]
    assert all(x.tier.value in "ABC" for x in s.sources)


def test_rental_has_no_series_or_source_median():
    s = mei(Scope.rental)
    assert s.monthly_series is None
    assert all(x.monthly_median is None for x in s.sources)


def test_mei_lending_series():
    s = mei(Scope.lending)
    assert [(m.month, m.amount) for m in s.monthly_series] == [
        ("2026-04", 2450), ("2026-05", 2300), ("2026-06", 2980),
        ("2026-07", 3100), ("2026-08", 2620), ("2026-09", 2780),
    ]
    assert all(isinstance(x.monthly_median, int) for x in s.sources)
