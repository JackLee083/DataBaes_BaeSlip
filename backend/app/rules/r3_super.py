"""R3 Payday Super receipt timing."""

from datetime import date, timedelta

from app.config import Config
from app.models import Check, Severity, SourceType, Worker


def add_business_days(start: date, days: int) -> date:
    """Count weekdays after start; skip weekends, but not public holidays."""
    result = start
    remaining = days
    while remaining > 0:
        result += timedelta(days=1)
        if result.weekday() < 5:
            remaining -= 1
    return result


def _business_days_late(deadline: date, received_on: date) -> int:
    """Count weekdays after the deadline through an observed receipt date."""
    return sum(
        current.weekday() < 5
        for current in (deadline + timedelta(days=offset) for offset in range(1, (received_on - deadline).days + 1))
    )


def _paydays(worker: Worker, employment_source_ids: set[str]) -> list[tuple[str, date]]:
    """Use income paydays; fall back to contribution records where income is absent."""
    income_paydays = {
        (income.source_id, income.paid_on)
        for income in worker.income
        if income.source_id in employment_source_ids
    }
    sources_with_income = {source_id for source_id, _ in income_paydays}
    contribution_paydays = {
        (contribution.source_id, contribution.payday)
        for contribution in worker.super_contributions
        if contribution.source_id in employment_source_ids
        and contribution.source_id not in sources_with_income
    }
    return sorted(income_paydays | contribution_paydays)


def _check(
    *,
    source_id: str,
    source_label: str,
    payday: date,
    deadline: date,
    cfg: Config,
    today: date,
    contribution_received_on: date | None,
    amount_cents: int | None,
) -> Check:
    observed_receipt = contribution_received_on if contribution_received_on and contribution_received_on <= today else None
    facts = {
        "source_id": source_id,
        "source_label": source_label,
        "payday": payday.isoformat(),
        "deadline": deadline.isoformat(),
        "business_days": cfg.super_deadline_business_days,
        "received_on": observed_receipt.isoformat() if observed_receipt else None,
        "note": "Weekends are skipped; public holidays are not.",
        "as_of": today.isoformat(),
    }
    if amount_cents is not None:
        facts["super_amount_cents"] = amount_cents
    if contribution_received_on and contribution_received_on > today:
        facts["reported_received_on"] = contribution_received_on.isoformat()

    if observed_receipt and observed_receipt > deadline:
        facts["business_days_late"] = _business_days_late(deadline, observed_receipt)
        facts["status"] = "received_late"
        severity = Severity.review
        title = "Super timing needs review"
    else:
        facts["status"] = "not_seen_as_of_today"
        severity = Severity.warning
        title = "Super receipt needs review"

    return Check(
        check_id=f"r3-{source_id}-{payday.isoformat()}",
        rule="R3",
        severity=severity,
        title=title,
        period_start=payday,
        period_end=deadline,
        facts=facts,
        possible_explanations=[
            "The super fund may have taken extra days to process the payment.",
            "The employer may use a clearing house that adds delay.",
        ],
        next_steps=[
            "Check the contribution date in your super fund account.",
            "Ask your employer when the contribution was sent.",
            "If it keeps happening, the ATO or a union can help.",
        ],
    )


def run(worker: Worker, cfg: Config) -> list[Check]:
    employment_sources = {
        source.source_id: source.label
        for source in worker.sources
        if source.type is SourceType.employment
    }
    contributions = {
        (contribution.source_id, contribution.payday): contribution
        for contribution in worker.super_contributions
    }
    checks = []
    for source_id, payday in _paydays(worker, set(employment_sources)):
        deadline = add_business_days(payday, cfg.super_deadline_business_days)
        contribution = contributions.get((source_id, payday))
        received_on = contribution.received_on if contribution else None
        if received_on is not None and received_on <= worker.today and received_on <= deadline:
            continue
        if received_on is None or received_on > worker.today:
            if worker.today <= deadline:
                continue
        checks.append(
            _check(
                source_id=source_id,
                source_label=employment_sources[source_id],
                payday=payday,
                deadline=deadline,
                cfg=cfg,
                today=worker.today,
                contribution_received_on=received_on,
                amount_cents=contribution.amount_cents if contribution else None,
            )
        )
    return checks
