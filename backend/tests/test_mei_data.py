"""data-1: the committed Mei mock data (app/data/mei.json) and its generator."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from app.models import Worker

BACKEND = Path(__file__).resolve().parent.parent
MEI = BACKEND / "app" / "data" / "mei.json"
FIXTURES = BACKEND.parent / "fixtures"
TODAY = date(2026, 9, 29)


def raw() -> dict:
    return json.loads(MEI.read_text(encoding="utf-8"))


def worker() -> Worker:
    return Worker.model_validate(raw())


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def course_breaks():
    try:
        from app.config import Config

        return Config().course_breaks
    except Exception:  # pragma: no cover
        return ((date(2026, 6, 20), date(2026, 7, 26)),)


def daily_hours(w: Worker) -> dict[date, float]:
    h: dict[date, float] = defaultdict(float)
    for s in w.shifts:
        h[s.date] += s.hours
    for d in w.platform_days:
        h[d.date] += d.online_minutes / 60
    for a, b in course_breaks():
        day = a
        while day <= b:
            h.pop(day, None)
            day += timedelta(days=1)
    return h


def window_total(h: dict[date, float], start: date) -> float:
    return sum(h.get(start + timedelta(days=i), 0.0) for i in range(14))


def test_parses_as_worker():
    w = worker()
    assert (w.worker_id, w.display_name, w.language, w.visa) == ("mei", "Mei L.", "en", "500")
    assert w.today == TODAY
    assert (w.period_start, w.period_end) == (date(2026, 4, 1), date(2026, 9, 30))
    assert [s.source_id for s in w.sources] == ["abc-cafe", "delivery-co", "studio-sg", "cash-tutoring"]
    assert len(w.income) == 48


def test_monthly_net_targets():
    w = worker()
    months: dict[str, int] = defaultdict(int)
    for r in w.income:
        if "self_reported" in [e.value for e in r.evidence]:
            continue
        months[r.paid_on.strftime("%Y-%m")] += r.net_cents
    assert [months[m] for m in ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]] == [
        245000, 230000, 298000, 310000, 262000, 278000,
    ]


def cafe_hours(w: Worker, a: date, b: date) -> float:
    return sum(s.hours for s in w.shifts if s.source_id == "abc-cafe" and not s.planned and a <= s.date <= b)


def test_r1_case_rows():
    w = worker()
    assert cafe_hours(w, date(2026, 9, 1), date(2026, 9, 14)) == 20
    assert cafe_hours(w, date(2026, 8, 18), date(2026, 8, 31)) == 20
    gross = {(r.period_start, r.period_end): r.gross_cents for r in w.income if r.source_id == "abc-cafe"}
    assert gross[(date(2026, 9, 1), date(2026, 9, 14))] == 44000
    assert gross[(date(2026, 8, 18), date(2026, 8, 31))] == 66100


def test_r2_week_0907():
    w = worker()
    days = [d for d in w.platform_days if date(2026, 9, 7) <= d.date <= date(2026, 9, 13)]
    assert sum(d.engaged_minutes for d in days) == 540
    p = [x for x in w.platform_payouts if x.week_start == date(2026, 9, 7)]
    assert len(p) == 1 and p[0].amount_cents == 25000 and p[0].paid_on == date(2026, 9, 14)


def test_r3_super_rows():
    w = worker()
    sup = {s.payday: s for s in w.super_contributions}
    assert len(w.super_contributions) == 12
    assert sup[date(2026, 9, 16)].received_on == date(2026, 9, 28)
    assert sup[date(2026, 9, 16)].amount_cents == 5280
    assert sup[date(2026, 9, 2)].received_on == date(2026, 9, 8)
    for s in w.super_contributions:
        gross = next(r.gross_cents for r in w.income if r.source_id == "abc-cafe" and r.paid_on == s.payday)
        assert s.amount_cents == round(gross * 0.12)


def test_r4_window_0928_is_50_and_strict_max():
    h = daily_hours(worker())
    start = date(2026, 9, 28)
    assert window_total(h, start) == 50
    others = [window_total(h, date(2026, 9, 16) + timedelta(days=i)) for i in range(12)]
    assert max(others) < 50


def test_past_windows_le_40():
    h = daily_hours(worker())
    start = date(2026, 3, 29)
    while start + timedelta(days=13) <= TODAY:
        assert window_total(h, start) <= 40 + 1e-9, start
        start += timedelta(days=1)


def test_platform_day_gross_sums_to_payout():
    w = worker()
    assert len(w.platform_payouts) == 26
    for p in w.platform_payouts:
        days = [d for d in w.platform_days if p.week_start <= d.date < p.week_start + timedelta(days=7)]
        assert len(days) == 3
        assert sum(d.gross_cents for d in days) == p.amount_cents
        assert p.paid_on == p.week_start + timedelta(days=7)
        assert all(d.online_minutes >= d.engaged_minutes for d in days)
    assert all(d.date <= date(2026, 9, 27) for d in w.platform_days)


def test_no_bank_deposit_in_raw_evidence():
    for r in raw()["income"]:
        assert "bank_deposit" not in r["evidence"]


def test_generator_matches_committed_file():
    from app.data import gen_mei

    assert gen_mei.build() == raw()
    assert MEI.read_text(encoding="utf-8") == json.dumps(gen_mei.build(), indent=2) + "\n"


def test_bank_deposits():
    w = worker()
    non_cash = [r for r in w.income if r.source_id != "cash-tutoring"]
    assert len(w.bank_deposits) == len(non_cash) + 3
    descs = {"abc-cafe": "ABC CAFE PAYROLL", "delivery-co": "DELIVERY CO PTY LTD PAYMENT", "studio-sg": "STUDIO SG PTE LTD INTL TFR"}
    for r in non_cash:
        off = 1 if r.source_id == "studio-sg" else 0
        assert any(
            d.description == descs[r.source_id] and d.amount_cents == r.net_cents and d.date == r.paid_on + timedelta(days=off)
            for d in w.bank_deposits
        ), r.record_id
    assert [d.deposit_id for d in w.bank_deposits] == [f"dep_{i:03d}" for i in range(1, len(w.bank_deposits) + 1)]
    assert [d.date for d in w.bank_deposits] == sorted(d.date for d in w.bank_deposits)
    assert {"RENT REFUND", "TRANSFER FROM L CHEN"} <= {d.description for d in w.bank_deposits}


# ---- fixture gates ----


def test_records_match_timeline_fixture():
    expected = []
    for r in fixture("timeline.json")["records"]:
        r = dict(r)
        r.pop("tier")
        r["evidence"] = [e for e in r["evidence"] if e != "bank_deposit"]
        expected.append(r)
    got = [
        {k: v for k, v in r.items() if v is not None or k in ()}
        for r in json.loads(worker().model_dump_json())["income"]
    ]
    assert len(got) == len(expected) == 48
    assert got == expected


def test_sources_match_timeline_fixture():
    exp = [{k: s[k] for k in ("source_id", "label", "type")} for s in fixture("timeline.json")["sources"]]
    assert raw()["sources"] == exp


def test_check_inputs_match_checks_fixture():
    checks = {c["rule"]: c for c in fixture("checks.json")["checks"]}
    w = worker()
    r1 = checks["R1"]["facts"]
    assert cafe_hours(w, date(2026, 9, 1), date(2026, 9, 14)) == r1["hours"] == 20
    rec = next(r for r in w.income if r.source_id == "abc-cafe" and r.period_start == date(2026, 9, 1))
    assert rec.gross_cents == r1["gross_cents"] == 44000
    r2 = checks["R2"]["facts"]
    days = [d for d in w.platform_days if date(2026, 9, 7) <= d.date <= date(2026, 9, 13)]
    assert sum(d.engaged_minutes for d in days) == r2["engaged_minutes"] == 540
    pay = next(p for p in w.platform_payouts if p.week_start == date(2026, 9, 7))
    assert pay.amount_cents == r2["payout_cents"] == 25000
    r3 = checks["R3"]["facts"]
    sup = {s.payday.isoformat(): s for s in w.super_contributions}
    assert sup[r3["payday"]].received_on.isoformat() == r3["received_on"] == "2026-09-28"
    assert sup["2026-09-02"].received_on == date(2026, 9, 8)
    r4 = checks["R4"]["facts"]
    planned = [
        {"date": s.date.isoformat(), "source_id": s.source_id, "hours": s.hours} for s in w.shifts if s.planned
    ]
    assert planned == r4["planned_shifts"]
    assert window_total(daily_hours(w), date.fromisoformat(r4["window_start"])) == r4["total_hours"] == 50


def test_no_date_after_today_except_planned():
    w = worker()
    dates = []
    for r in w.income:
        dates += [r.period_start, r.period_end, r.paid_on]
    dates += [s.date for s in w.shifts if not s.planned]
    dates += [d.date for d in w.platform_days]
    for p in w.platform_payouts:
        dates += [p.paid_on]
    for s in w.super_contributions:
        dates += [s.payday] + ([s.received_on] if s.received_on else [])
    dates += [d.date for d in w.bank_deposits]
    late = [d for d in dates if d > TODAY]
    assert late == [], late
