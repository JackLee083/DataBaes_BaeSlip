from datetime import date

from app.models import Tier, TimelineRecord
from app.services.summary import monthly_totals, months_in_period, summarize

START, END = date(2026, 4, 1), date(2026, 9, 30)


def rec(paid_on: date, cents: int, tier: Tier = Tier.A, i: int = 1) -> TimelineRecord:
    return TimelineRecord(
        record_id=f"inc_{i:03d}",
        source_id="src_1",
        period_start=paid_on,
        period_end=paid_on,
        gross_cents=cents,
        net_cents=cents,
        paid_on=paid_on,
        evidence=[],
        tier=tier,
    )


def guide_records() -> list[TimelineRecord]:
    cents = [245000, 230000, 298000, 310000, 262000, 278000]
    return [rec(date(2026, 4 + i, 15), c, i=i) for i, c in enumerate(cents)]


def test_guide_targets():
    totals = monthly_totals(guide_records(), START, END)
    assert list(totals) == [f"2026-0{m}" for m in range(4, 10)]
    s = summarize(totals, months_in_period(START, END))
    assert (s.monthly_income_range.low, s.monthly_income_range.high) == (2300, 3100)
    assert s.monthly_median == 2700
    assert (s.coverage.months_with_data, s.coverage.months_in_period) == (6, 6)
    assert s.currency == "AUD"


def test_d_excluded():
    recs = guide_records() + [rec(date(2026, 4, 20), 99999, Tier.D, i=50)]
    totals = monthly_totals(recs, START, END)
    assert totals["2026-04"] == 245000
    assert "2026-04" in monthly_totals(recs, START, END, min_tier="D")
    assert monthly_totals(recs, START, END, min_tier="D")["2026-04"] == 344999


def test_outside_period_excluded():
    recs = guide_records() + [rec(date(2026, 3, 31), 5000, i=60), rec(date(2026, 10, 1), 5000, i=61)]
    totals = monthly_totals(recs, START, END)
    assert "2026-03" not in totals and "2026-10" not in totals
    assert len(totals) == 6


def test_cents_rounded_to_dollars():
    s = summarize({"2026-04": 12349, "2026-05": 12351}, 2)
    assert s.monthly_income_range.low == 123
    assert s.monthly_income_range.high == 124
    assert s.monthly_median == 124  # median of [123, 124] = 123.5 -> round half to even = 124


def test_months_in_period():
    assert months_in_period(START, END) == 6
    assert months_in_period(date(2026, 4, 15), date(2026, 4, 20)) == 1
    assert months_in_period(date(2025, 11, 1), date(2026, 2, 1)) == 4
