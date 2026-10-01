import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from app.config import Config
from app.models import Check, IncomeSource, PlatformDay, PlatformPayout, Severity, SourceType, Worker
from app.rules.r2_delivery import run

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "checks.json"
WEEK = date(2026, 9, 7)  # a Monday


def worker(*, days, payouts, sources=None):
    if sources is None:
        sources = [IncomeSource(source_id="delivery-co", label="Food delivery platform",
                                type=SourceType.platform)]
    return Worker(
        worker_id="test-worker", display_name="Test Worker", language="en", visa=None,
        today=date(2026, 9, 29), period_start=date(2026, 8, 1), period_end=date(2026, 9, 30),
        sources=sources, income=[], shifts=[], platform_days=list(days),
        platform_payouts=list(payouts), super_contributions=[], bank_deposits=[],
    )


def day(d, engaged, *, online=None, source="delivery-co"):
    return PlatformDay(date=d, source_id=source, engaged_minutes=engaged,
                       online_minutes=engaged if online is None else online, gross_cents=0)


def payout(amount, *, week=WEEK, source="delivery-co"):
    return PlatformPayout(source_id=source, week_start=week, amount_cents=amount,
                          paid_on=week + timedelta(days=7))


def demo_worker(amount=25000):
    return worker(
        days=[day(WEEK, 300), day(date(2026, 9, 10), 240)],
        payouts=[payout(amount)],
    )


def test_delivery_difference_3170():
    checks = run(demo_worker(), Config())

    assert len(checks) == 1
    c = checks[0]
    assert c.check_id == "r2-delivery-co-2026-09-07"
    assert c.rule == "R2"
    assert c.severity == Severity.review
    assert c.title == "Delivery pay may be below the minimum for engaged time"
    assert (c.period_start, c.period_end) == (date(2026, 9, 7), date(2026, 9, 13))
    assert (c.expected_cents, c.actual_cents, c.difference_cents) == (28170, 25000, 3170)


def test_normal_payout_produces_no_check():
    assert run(demo_worker(28170), Config()) == []
    assert run(demo_worker(30000), Config()) == []


def test_tolerance_boundary():
    cfg = Config()
    assert run(demo_worker(28170 - cfg.tolerance_cents), cfg) == []
    assert len(run(demo_worker(28170 - cfg.tolerance_cents - 1), cfg)) == 1


def test_source_and_week_isolation():
    other = IncomeSource(source_id="other-co", label="Other", type=SourceType.platform)
    base = IncomeSource(source_id="delivery-co", label="Food delivery platform",
                        type=SourceType.platform)
    subject = worker(
        sources=[base, other],
        days=[
            day(WEEK, 540),
            day(WEEK + timedelta(days=6), 60),          # Sunday, counted
            day(WEEK - timedelta(days=1), 600),         # previous Sunday, not counted
            day(WEEK + timedelta(days=7), 600),         # next Monday, not counted
            day(WEEK, 1000, source="other-co"),         # other source, not counted
        ],
        payouts=[payout(0), payout(0, source="other-co")],
    )

    checks = run(subject, Config())

    by_id = {c.check_id: c for c in checks}
    assert by_id["r2-delivery-co-2026-09-07"].facts["engaged_minutes"] == 600
    assert by_id["r2-other-co-2026-09-07"].facts["engaged_minutes"] == 1000
    assert [c.check_id for c in checks] == ["r2-delivery-co-2026-09-07", "r2-other-co-2026-09-07"]


def test_output_sorted_by_week_then_source():
    other = IncomeSource(source_id="a-co", label="A", type=SourceType.platform)
    base = IncomeSource(source_id="delivery-co", label="D", type=SourceType.platform)
    w2 = WEEK + timedelta(days=7)
    subject = worker(
        sources=[base, other],
        days=[day(w2, 600, source="a-co"), day(w2, 600), day(WEEK, 600)],
        payouts=[payout(0, week=w2), payout(0, week=w2, source="a-co"), payout(0)],
    )

    ids = [c.check_id for c in run(subject, Config())]

    assert ids == ["r2-delivery-co-2026-09-07", "r2-a-co-2026-09-14", "r2-delivery-co-2026-09-14"]


def test_configured_rate_is_used():
    cfg = replace(Config(), delivery_min_per_engaged_hour_cents=4000)

    c = run(demo_worker(), cfg)[0]

    assert c.expected_cents == 36000
    assert c.difference_cents == 11000
    assert c.facts["min_per_engaged_hour_cents"] == 4000


def test_rounding_half_up_with_integers():
    # 1 minute at 3130 c/h = 52.1667 -> 52; 3 minutes at 3150 c/h = 157.5 -> 158
    cfg = replace(Config(), delivery_min_per_engaged_hour_cents=3150, tolerance_cents=0)
    subject = worker(days=[day(WEEK, 3)], payouts=[payout(0)])

    c = run(subject, cfg)[0]

    assert c.expected_cents == 158
    assert isinstance(c.expected_cents, int)


def test_online_minutes_do_not_change_result():
    subject = worker(
        days=[day(WEEK, 300, online=5000), day(date(2026, 9, 10), 240, online=9000)],
        payouts=[payout(25000)],
    )

    c = run(subject, Config())[0]

    assert (c.expected_cents, c.difference_cents) == (28170, 3170)
    assert c.facts["engaged_minutes"] == 540


def test_unverifiable_weeks_emit_nothing():
    # Payout with no engaged minutes, and engaged minutes with no payout row.
    no_engaged = worker(days=[day(WEEK, 0, online=400)], payouts=[payout(0)])
    no_payout = worker(days=[day(WEEK, 540)], payouts=[])
    no_days = worker(days=[], payouts=[payout(0)])

    assert run(no_engaged, Config()) == []
    assert run(no_payout, Config()) == []
    assert run(no_days, Config()) == []


def test_non_platform_sources_ignored():
    emp = IncomeSource(source_id="delivery-co", label="X", type=SourceType.employment)
    subject = worker(sources=[emp], days=[day(WEEK, 540)], payouts=[payout(0)])

    assert run(subject, Config()) == []


def test_output_validates_and_input_unchanged():
    subject = demo_worker()
    before = subject.model_dump()

    checks = run(subject, Config())

    assert subject.model_dump() == before
    for c in checks:
        assert Check.model_validate(c.model_dump()) == c
        text = json.dumps(c.model_dump(mode="json")).lower()
        for word in ("violated", "stole", "illegal", "breach"):
            assert word not in text


def test_matches_fixture_entry():
    expected = next(
        c for c in json.loads(FIXTURE.read_text(encoding="utf-8"))["checks"]
        if c["check_id"] == "r2-delivery-co-2026-09-07"
    )

    produced = run(demo_worker(), Config())[0]

    assert produced.model_dump(mode="json") == expected
