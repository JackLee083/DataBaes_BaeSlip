from datetime import date

from app.config import Config
from app.models import BankDeposit, Evidence, IncomeRecord, IncomeSource, SourceType, WorkShift, Worker
from app.rules.r1_min_wage import run


def worker(*, income, shifts, deposits=(), primary_source_type=SourceType.employment):
    return Worker(
        worker_id="test-worker",
        display_name="Test Worker",
        language="en",
        visa=None,
        today=date(2026, 9, 29),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 9, 30),
        sources=[IncomeSource(source_id="abc-cafe", label="ABC Cafe", type=primary_source_type),
                 IncomeSource(source_id="other-job", label="Other job", type=SourceType.employment)],
        income=list(income),
        shifts=list(shifts),
        platform_days=[],
        platform_payouts=[],
        super_contributions=[],
        bank_deposits=list(deposits),
    )


def record(*, start=date(2026, 9, 1), end=date(2026, 9, 14), gross=44000,
           net=44000, paid_on=date(2026, 9, 16), evidence=(Evidence.stp_income_statement,),
           currency="AUD"):
    return IncomeRecord(
        record_id="income-1", source_id="abc-cafe", period_start=start, period_end=end,
        gross_cents=gross, net_cents=net, paid_on=paid_on, evidence=list(evidence), currency=currency,
    )


def shift(day, hours, *, source="abc-cafe", planned=False):
    return WorkShift(date=day, hours=hours, source_id=source, planned=planned)


def test_underpayment_difference_22100():
    subject = worker(
        income=[record()],
        shifts=[shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)],
    )

    checks = run(subject, Config())

    assert len(checks) == 1
    check = checks[0]
    assert check.check_id == "r1-abc-cafe-2026-09-01"
    assert check.rule == "R1"
    assert check.severity == "review"
    assert check.title == "Pay may be below the minimum rate"
    assert (check.expected_cents, check.actual_cents, check.difference_cents) == (66100, 44000, 22100)
    assert check.facts["hours"] == 20
    assert check.facts["min_hourly_cents"] == 3305
    assert check.facts["actual_basis"] == "stp_income_statement"
    assert check.facts["gross_cents"] == 44000
    assert check.facts["source_label"] == "ABC Cafe"
    assert check.facts["paid_on"] == date(2026, 9, 16)
    assert check.facts["award_limitation"]


def test_normal_period_produces_no_check():
    subject = worker(
        income=[record(start=date(2026, 8, 18), end=date(2026, 8, 31), gross=66100, net=66100,
                       paid_on=date(2026, 9, 2))],
        shifts=[shift(date(2026, 8, 18), 10), shift(date(2026, 8, 31), 10)],
    )

    assert run(subject, Config()) == []


def test_only_actual_same_source_in_period_shifts_are_counted():
    subject = worker(
        income=[record()],
        shifts=[
            shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10),
            shift(date(2026, 9, 15), 20), shift(date(2026, 9, 5), 20, planned=True),
            shift(date(2026, 9, 5), 20, source="other-job"),
        ],
    )

    assert run(subject, Config())[0].expected_cents == 66100


def test_tolerance_boundary_is_strict_and_configured_rate_is_used():
    shifts = [shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)]
    no_alert = worker(income=[record(gross=66000, net=66000)], shifts=shifts)
    alert = worker(income=[record(gross=65999, net=65999)], shifts=shifts)
    custom = worker(income=[record(gross=39899, net=39899)], shifts=shifts)

    assert run(no_alert, Config()) == []
    assert run(alert, Config())[0].difference_cents == 101
    assert run(custom, Config(min_casual_hourly_cents=2000))[0].expected_cents == 40000


def test_matched_aud_bank_deposit_is_used_when_stp_is_absent():
    subject = worker(
        income=[record(evidence=(), gross=1, net=44000)],
        shifts=[shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)],
        deposits=[BankDeposit(deposit_id="dep-1", date=date(2026, 9, 18),
                              description="ABC CAFE PAYROLL", amount_cents=44050)],
    )

    check = run(subject, Config())[0]
    assert (check.actual_cents, check.difference_cents) == (44050, 22050)
    assert check.facts["actual_basis"] == "matched_bank_deposit_net_proxy"
    assert check.facts["gross_cents"] == 44050
    assert check.facts["verification_status"] == "matched_bank_deposit"
    assert check.facts["bank_deposit_net_proxy_limitation"]
    assert run(subject, Config(tolerance_cents=49))[0].severity == "info"


def test_bank_match_requires_normalized_payer_amount_and_date_constraints():
    base_income = [record(evidence=(), gross=1, net=44000)]
    shifts = [shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)]
    deposits = [
        BankDeposit(deposit_id="wrong-name", date=date(2026, 9, 17), description="OTHER CAFE", amount_cents=44000),
        BankDeposit(deposit_id="wrong-amount", date=date(2026, 9, 17), description="ABC CAFE PTY LTD", amount_cents=44101),
        BankDeposit(deposit_id="wrong-date", date=date(2026, 9, 20), description="ABC CAFE PAYMENT", amount_cents=44000),
    ]

    check = run(worker(income=base_income, shifts=shifts, deposits=deposits), Config())[0]
    assert check.severity == "info"
    assert check.facts["verification_status"] == "unmatched_bank_deposit"


def test_bank_fallback_requires_an_aud_record():
    subject = worker(
        income=[record(evidence=(), gross=1, net=44000, currency="USD")],
        shifts=[shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)],
        deposits=[BankDeposit(deposit_id="dep-1", date=date(2026, 9, 17),
                              description="ABC CAFE PAYROLL", amount_cents=44000)],
    )

    assert run(subject, Config())[0].facts["verification_status"] == "unmatched_bank_deposit"


def test_unmatched_bank_is_info_with_unknown_actual_and_difference():
    subject = worker(
        income=[record(evidence=(Evidence.notice_of_assessment,), gross=44000, net=44000)],
        shifts=[shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)],
        deposits=[BankDeposit(deposit_id="unrelated", date=date(2026, 9, 17),
                              description="OTHER COMPANY", amount_cents=44000)],
    )

    checks = run(subject, Config())

    assert len(checks) == 1
    check = checks[0]
    assert (check.rule, check.severity, check.title) == (
        "R1", "info", "Unable to verify pay against the minimum rate",
    )
    assert (check.expected_cents, check.actual_cents, check.difference_cents) == (66100, None, None)
    assert check.facts["source_id"] == "abc-cafe"
    assert check.facts["hours"] == 20
    assert check.facts["min_hourly_cents"] == 3305
    assert check.facts["actual_basis"] == "unverified"
    assert check.facts["verification_status"] == "unmatched_bank_deposit"
    assert "gross_cents" not in check.facts
    assert "net_cents" not in check.facts
    assert any("payslip" in step.lower() for step in check.next_steps)


def test_shifts_without_an_employment_income_record_do_not_create_a_pay_period():
    subject = worker(income=[], shifts=[shift(date(2026, 9, 1), 20)])

    assert run(subject, Config()) == []


def test_non_employment_income_record_is_not_checked_by_r1():
    subject = worker(
        income=[record()],
        shifts=[shift(date(2026, 9, 1), 10), shift(date(2026, 9, 14), 10)],
        primary_source_type=SourceType.contract,
    )

    assert run(subject, Config()) == []
