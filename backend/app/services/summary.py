"""Monthly totals, range, median, coverage; the timeline (BUILD_GUIDE 5.3).
Owner: data (B3, B12). Stub. interfaces.build_timeline and interfaces.summarize_worker
delegate here."""

import statistics
from collections import defaultdict
from datetime import date

from app.models import (
    Coverage,
    MoneyRange,
    MonthAmount,
    Period,
    Scope,
    SourceSummary,
    Summary,
    Tier,
    TimelineMonth,
    TimelineRecord,
    TimelineResponse,
    Worker,
    WorkerSummary,
)
from app.services import tiers


def period_months(start: date, end: date) -> list[str]:
    """Calendar months touched by [start, end], as "YYYY-MM"."""
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def months_in_period(start: date, end: date) -> int:
    return len(period_months(start, end))


def monthly_totals(
    records: list[TimelineRecord], period_start: date, period_end: date, min_tier: str = "C"
) -> dict[str, int]:
    """Net cents by paid_on month, only records at min_tier or stronger."""
    rank = "ABCD".index(min_tier)
    totals: dict[str, int] = defaultdict(int)
    for r in records:
        if period_start <= r.paid_on <= period_end and "ABCD".index(r.tier.value) <= rank:
            totals[r.paid_on.strftime("%Y-%m")] += r.net_cents
    return dict(sorted(totals.items()))


def summarize(totals_cents: dict[str, int], months_in_period: int) -> Summary:
    dollars = [round(v / 100) for v in totals_cents.values()]
    return Summary(
        currency="AUD",
        monthly_income_range=MoneyRange(low=min(dollars), high=max(dollars)),
        monthly_median=round(statistics.median(dollars)),
        coverage=Coverage(months_with_data=len(dollars), months_in_period=months_in_period),
    )


def build_timeline(worker: Worker) -> TimelineResponse:
    t = tiers.tier_worker(worker)
    start, end = worker.period_start, worker.period_end
    months = {m: TimelineMonth(net_cents=0, self_reported_cents=0) for m in period_months(start, end)}
    for r in t.records:
        if not (start <= r.paid_on <= end):
            continue
        month = months[r.paid_on.strftime("%Y-%m")]
        if r.tier == Tier.D:
            month.self_reported_cents += r.net_cents
        else:
            month.net_cents += r.net_cents
    return TimelineResponse(
        worker_id=worker.worker_id,
        display_name=worker.display_name,
        language=worker.language,
        period=Period(start=start, end=end),
        sources=t.sources,
        records=t.records,
        months=months,
    )


def summarize_worker(worker: Worker, scope: Scope) -> WorkerSummary:
    t = tiers.tier_worker(worker)
    start, end = worker.period_start, worker.period_end
    totals = monthly_totals(t.records, start, end)
    lending = scope == Scope.lending

    per_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in t.records:
        if start <= r.paid_on <= end and r.tier != Tier.D:
            per_source[r.source_id][r.paid_on.strftime("%Y-%m")] += r.net_cents

    sources = []
    for s in t.sources:
        if s.tier == Tier.D:
            continue
        median = None
        if lending and per_source[s.source_id]:
            median = round(statistics.median(round(c / 100) for c in per_source[s.source_id].values()))
        sources.append(
            SourceSummary(
                source_id=s.source_id, label=s.label, type=s.type, tier=s.tier,
                evidence=s.evidence, monthly_median=median,
            )
        )
    return WorkerSummary(
        period=Period(start=start, end=end),
        sources=sources,
        summary=summarize(totals, months_in_period(start, end)),
        monthly_series=[MonthAmount(month=m, amount=round(c / 100)) for m, c in totals.items()] if lending else None,
    )
