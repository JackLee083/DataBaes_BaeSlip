from datetime import date

from app.config import Config
from app.models import Evidence, IncomeRecord, IncomeSource, SourceType, SuperContribution, Worker
from app.rules.r3_super import run


def worker_with(*, today=date(2026, 9, 29), contributions=(), paydays=()):
    return Worker(
        worker_id="mei",
        display_name="Mei L.",
        language="zh-Hant",
        visa="500",
        today=today,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 9, 30),
        sources=[
            IncomeSource(
                source_id="abc-cafe",
                label="Hospitality (casual)",
                type=SourceType.employment,
            )
        ],
        income=[
            IncomeRecord(
                record_id=f"income-{payday.isoformat()}",
                source_id="abc-cafe",
                period_start=payday,
                period_end=payday,
                gross_cents=44000,
                net_cents=44000,
                paid_on=payday,
                evidence=[Evidence.stp_income_statement],
            )
            for payday in paydays
        ],
        shifts=[],
        platform_days=[],
        platform_payouts=[],
        super_contributions=list(contributions),
        bank_deposits=[],
    )


def test_late_receipt_review_with_deadline_2026_09_25():
    worker = worker_with(
        contributions=[
            SuperContribution(
                source_id="abc-cafe",
                payday=date(2026, 9, 16),
                amount_cents=5280,
                received_on=date(2026, 9, 28),
            )
        ],
        paydays=[date(2026, 9, 16)],
    )

    checks = run(worker, Config())

    assert len(checks) == 1
    check = checks[0]
    assert check.check_id == "r3-abc-cafe-2026-09-16"
    assert check.rule == "R3"
    assert check.severity.value == "review"
    assert check.title == "Super timing needs review"
    assert (check.period_start, check.period_end) == (date(2026, 9, 16), date(2026, 9, 25))
    assert check.expected_cents is check.actual_cents is check.difference_cents is None
    assert check.facts == {
        "source_id": "abc-cafe",
        "source_label": "Hospitality (casual)",
        "payday": "2026-09-16",
        "deadline": "2026-09-25",
        "business_days": 7,
        "received_on": "2026-09-28",
        "super_amount_cents": 5280,
        "note": "Weekends are skipped; public holidays are not.",
        "business_days_late": 1,
        "as_of": "2026-09-29",
        "status": "received_late",
    }


def test_add_business_days_counts_weekdays_after_payday():
    from app.rules.r3_super import add_business_days

    assert add_business_days(date(2026, 9, 16), 7) == date(2026, 9, 25)
    assert add_business_days(date(2026, 9, 18), 1) == date(2026, 9, 21)


def test_normal_receipt_on_or_before_deadline_has_no_check():
    worker = worker_with(
        contributions=[
            SuperContribution(
                source_id="abc-cafe",
                payday=date(2026, 9, 2),
                amount_cents=5280,
                received_on=date(2026, 9, 8),
            )
        ],
        paydays=[date(2026, 9, 2)],
    )

    assert run(worker, Config()) == []


def test_missing_receipt_warns_only_after_deadline():
    payday = date(2026, 9, 16)
    contribution = SuperContribution(
        source_id="abc-cafe", payday=payday, amount_cents=5280, received_on=None
    )

    assert run(worker_with(today=date(2026, 9, 24), contributions=[contribution], paydays=[payday]), Config()) == []
    assert run(worker_with(today=date(2026, 9, 25), contributions=[contribution], paydays=[payday]), Config()) == []
    checks = run(worker_with(today=date(2026, 9, 26), contributions=[contribution], paydays=[payday]), Config())

    assert len(checks) == 1
    assert checks[0].severity.value == "warning"
    assert checks[0].title == "Super receipt needs review"
    assert checks[0].facts["received_on"] is None
    assert checks[0].facts["status"] == "not_seen_as_of_today"


def test_future_receipt_is_not_arrived_as_of_today():
    worker = worker_with(
        contributions=[
            SuperContribution(
                source_id="abc-cafe",
                payday=date(2026, 9, 16),
                amount_cents=5280,
                received_on=date(2026, 9, 30),
            )
        ],
        paydays=[date(2026, 9, 16)],
    )

    checks = run(worker, Config())

    assert len(checks) == 1
    assert checks[0].severity.value == "warning"
    assert checks[0].title == "Super receipt needs review"
    assert checks[0].facts["received_on"] is None
    assert checks[0].facts["reported_received_on"] == "2026-09-30"
    assert checks[0].facts["status"] == "not_seen_as_of_today"


def test_matches_contribution_by_both_source_and_payday():
    worker = worker_with(
        contributions=[
            SuperContribution(
                source_id="other-cafe",
                payday=date(2026, 9, 16),
                amount_cents=5280,
                received_on=date(2026, 9, 17),
            ),
            SuperContribution(
                source_id="abc-cafe",
                payday=date(2026, 9, 15),
                amount_cents=5280,
                received_on=date(2026, 9, 17),
            ),
        ],
        paydays=[date(2026, 9, 16)],
    )

    checks = run(worker, Config())

    assert len(checks) == 1
    assert checks[0].severity.value == "warning"
    assert checks[0].facts["status"] == "not_seen_as_of_today"


def test_uses_configured_business_day_count():
    worker = worker_with(
        contributions=[
            SuperContribution(
                source_id="abc-cafe",
                payday=date(2026, 9, 16),
                amount_cents=5280,
                received_on=date(2026, 9, 22),
            )
        ],
        paydays=[date(2026, 9, 16)],
    )

    assert run(worker, Config(super_deadline_business_days=4)) == []


def test_absent_contribution_warns_for_employment_payday():
    checks = run(worker_with(paydays=[date(2026, 9, 16)]), Config())

    assert len(checks) == 1
    assert checks[0].severity.value == "warning"
    assert checks[0].facts["received_on"] is None
    assert checks[0].facts["status"] == "not_seen_as_of_today"
    assert "super_amount_cents" not in checks[0].facts
