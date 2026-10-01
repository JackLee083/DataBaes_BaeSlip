"""R1 minimum casual hourly rate.

The rule is deliberately limited to the configured casual floor.  An award or
agreement can set a different rate, so every result preserves that limitation.
"""

from __future__ import annotations

from datetime import timedelta

from app.config import Config
from app.models import Check, Evidence, IncomeRecord, Severity, SourceType, Worker


def _normalize(name: str) -> str:
    """Normalize names according to BUILD_GUIDE section 5.2."""
    normalized = "".join(char for char in name.lower() if char.isalnum() or char == " ")
    for suffix in (" pty ltd", " pty", " ltd", " payroll", " payment"):
        normalized = normalized.replace(suffix, "")
    return " ".join(normalized.split())


def _matched_deposit_amount(worker: Worker, record: IncomeRecord, cfg: Config) -> int | None:
    """Return a verified AUD bank-deposit proxy for this record, if available."""
    if record.currency != "AUD":
        return None
    payer_name = record.source_id.replace("-", " ")
    normalized_payer = _normalize(payer_name)
    if not normalized_payer:
        return None
    latest_date = record.paid_on + timedelta(days=3)
    for deposit in worker.bank_deposits:
        if (
            abs(deposit.amount_cents - record.net_cents) <= cfg.tolerance_cents
            and record.paid_on <= deposit.date <= latest_date
            and normalized_payer in _normalize(deposit.description)
        ):
            return deposit.amount_cents
    return None


def _facts(*, worker: Worker, record: IncomeRecord, hours: float, cfg: Config, actual_basis: str,
           verification_status: str, actual_cents: int | None = None) -> dict[str, object]:
    source_label = next(
        source.label for source in worker.sources if source.source_id == record.source_id
    )
    facts: dict[str, object] = {
        "source_id": record.source_id,
        "source_label": source_label,
        "hours": hours,
        "min_hourly_cents": cfg.min_casual_hourly_cents,
        "period_start": record.period_start,
        "period_end": record.period_end,
        "paid_on": record.paid_on,
        "actual_basis": actual_basis,
        "verification_status": verification_status,
        "award_limitation": (
            "This configured casual minimum may not apply where an award or agreement applies."
        ),
    }
    if actual_cents is not None:
        facts["gross_cents"] = actual_cents
    return facts


def _explanations() -> list[str]:
    return [
        "An applicable award or enterprise agreement may set a different rate.",
        "Deductions may affect the amount received.",
        "Rostered hours may differ from hours actually worked.",
        "The payment may relate to a different pay period.",
    ]


def _review_steps() -> list[str]:
    return [
        "Check the Fair Work Pay Calculator for the applicable rate.",
        "Keep payslips, rosters, and records of hours worked.",
        "Consider support from a union or community legal centre.",
    ]


def _unverified_steps() -> list[str]:
    return [
        "Ask for a payslip or bank evidence for this pay period.",
        "Confirm which pay period the payment relates to.",
        "Keep rosters and records of hours worked.",
    ]


def run(worker: Worker, cfg: Config) -> list[Check]:
    employment_sources = {
        source.source_id for source in worker.sources if source.type == SourceType.employment
    }
    checks: list[Check] = []

    for record in worker.income:
        if record.source_id not in employment_sources:
            continue

        hours = sum(
            shift.hours
            for shift in worker.shifts
            if (
                shift.source_id == record.source_id
                and not shift.planned
                and record.period_start <= shift.date <= record.period_end
            )
        )
        expected = round(hours * cfg.min_casual_hourly_cents)
        check_id = f"r1-{record.source_id}-{record.period_start.isoformat()}"

        if Evidence.stp_income_statement in record.evidence:
            actual = record.gross_cents
            facts = _facts(
                record=record,
                worker=worker,
                hours=hours,
                cfg=cfg,
                actual_basis="stp_income_statement",
                verification_status="stp_income_statement",
                actual_cents=actual,
            )
        else:
            actual = _matched_deposit_amount(worker, record, cfg)
            if actual is None:
                checks.append(
                    Check(
                        check_id=check_id,
                        rule="R1",
                        severity=Severity.info,
                        title="Unable to verify pay against the minimum rate",
                        period_start=record.period_start,
                        period_end=record.period_end,
                        expected_cents=expected,
                        facts=_facts(
                            record=record,
                            worker=worker,
                            hours=hours,
                            cfg=cfg,
                            actual_basis="unverified",
                            verification_status="unmatched_bank_deposit",
                        ),
                        possible_explanations=[
                            "No payslip, STP income statement, or matching bank deposit was available."
                        ],
                        next_steps=_unverified_steps(),
                    )
                )
                continue
            facts = _facts(
                record=record,
                worker=worker,
                hours=hours,
                cfg=cfg,
                actual_basis="matched_bank_deposit_net_proxy",
                verification_status="matched_bank_deposit",
                actual_cents=actual,
            )
            facts["bank_deposit_net_proxy_limitation"] = (
                "A matched bank deposit is a net-payment proxy, not verified gross pay."
            )

        difference = expected - actual
        if difference > cfg.tolerance_cents:
            checks.append(
                Check(
                    check_id=check_id,
                    rule="R1",
                    severity=Severity.review,
                    title="Pay may be below the minimum rate",
                    period_start=record.period_start,
                    period_end=record.period_end,
                    expected_cents=expected,
                    actual_cents=actual,
                    difference_cents=difference,
                    facts=facts,
                    possible_explanations=_explanations(),
                    next_steps=_review_steps(),
                )
            )

    return checks
