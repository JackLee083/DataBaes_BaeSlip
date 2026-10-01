import json
import re
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from app import interfaces, rules
from app.config import Config, get_config
from app.models import (
    Check, Evidence, IncomeRecord, IncomeSource, PlatformDay, PlatformPayout,
    SourceType, SuperContribution, WorkShift, Worker,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "checks.json"
WEEK = date(2026, 9, 7)
PLANNED = [
    (date(2026, 9, 30), 8), (date(2026, 10, 1), 8), (date(2026, 10, 3), 6),
    (date(2026, 10, 4), 4), (date(2026, 10, 5), 4), (date(2026, 10, 7), 6),
    (date(2026, 10, 9), 4), (date(2026, 10, 10), 6), (date(2026, 10, 11), 4),
]
EXPECTED_IDS = [
    "r1-abc-cafe-2026-09-01", "r2-delivery-co-2026-09-07",
    "r3-abc-cafe-2026-09-16", "r4-all-2026-09-28",
]


def make_worker(*, problems=True) -> Worker:
    sources = [
        IncomeSource(source_id="abc-cafe", label="Hospitality (casual)", type=SourceType.employment),
        IncomeSource(source_id="delivery-co", label="Food delivery platform", type=SourceType.platform),
    ]
    income, shifts, days, payouts, supers = [], [], [], [], []
    payday = date(2026, 9, 16)
    income.append(IncomeRecord(
        record_id="income-1", source_id="abc-cafe",
        period_start=date(2026, 9, 1), period_end=date(2026, 9, 14),
        gross_cents=44000 if problems else 80000, net_cents=44000 if problems else 80000,
        paid_on=payday, evidence=[Evidence.stp_income_statement],
    ))
    shifts += [WorkShift(date=date(2026, 9, 1), hours=10, source_id="abc-cafe"),
               WorkShift(date=date(2026, 9, 14), hours=10, source_id="abc-cafe")]
    days += [
        PlatformDay(date=WEEK, source_id="delivery-co", engaged_minutes=300, online_minutes=300, gross_cents=0),
        PlatformDay(date=date(2026, 9, 10), source_id="delivery-co", engaged_minutes=240, online_minutes=240, gross_cents=0),
    ]
    payouts.append(PlatformPayout(source_id="delivery-co", week_start=WEEK,
                                  amount_cents=25000 if problems else 30000,
                                  paid_on=WEEK + timedelta(days=7)))
    supers.append(SuperContribution(source_id="abc-cafe", payday=payday, amount_cents=5280,
                                    received_on=date(2026, 9, 28) if problems else date(2026, 9, 20)))
    if problems:
        shifts += [WorkShift(date=d, hours=h, source_id="abc-cafe", planned=True) for d, h in PLANNED]
    return Worker(
        worker_id="mei", display_name="Mei L.", language="zh-Hant", visa="500",
        today=date(2026, 9, 29), period_start=date(2026, 4, 1), period_end=date(2026, 9, 30),
        sources=sources, income=income, shifts=shifts, platform_days=days,
        platform_payouts=payouts, super_contributions=supers, bank_deposits=[],
    )


def test_run_all_checks_returns_four_demo_alerts():
    checks = rules.run_all_checks(make_worker(), Config())

    ids = [c.check_id for c in checks]
    fixture_ids = [c["check_id"] for c in json.loads(FIXTURE.read_text(encoding="utf-8"))["checks"]]
    assert ids == EXPECTED_IDS
    assert set(ids) == set(fixture_ids)
    assert len(set(ids)) == 4
    assert [c.rule for c in checks] == ["R1", "R2", "R3", "R4"]
    assert (checks[0].expected_cents, checks[0].difference_cents) == (66100, 22100)
    assert checks[1].difference_cents == 3170
    assert checks[2].period_end == date(2026, 9, 25)
    assert checks[3].facts["total_hours"] == 50
    for c in checks:
        Check.model_validate(c.model_dump())
        assert re.search(r"\b(may|needs review|unable to verify)\b", c.title, re.I), c.title
        assert not re.search(r"violated|stole|steal|illegal|breach", c.title, re.I), c.title


def test_worker_is_not_mutated():
    w = make_worker()
    before = w.model_dump()
    rules.run_all_checks(w, Config())
    assert w.model_dump() == before


def test_deterministic():
    w = make_worker()
    first = [c.model_dump() for c in rules.run_all_checks(w, Config())]
    second = [c.model_dump() for c in rules.run_all_checks(w, Config())]
    assert first == second


def test_clean_worker_gives_no_checks():
    assert rules.run_all_checks(make_worker(problems=False), Config()) == []


def test_interfaces_default_cfg_matches_get_config():
    w = make_worker()
    assert interfaces.run_all_checks(w) == rules.run_all_checks(w, get_config())


def test_explicit_cfg_is_passed_through():
    w = make_worker()
    base = Config()
    huge = replace(base, tolerance_cents=10_000_000)
    assert len(interfaces.run_all_checks(w, base)) == 4
    assert [c.rule for c in interfaces.run_all_checks(w, huge)] == ["R3", "R4"]
