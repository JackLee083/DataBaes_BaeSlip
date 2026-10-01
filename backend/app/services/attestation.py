"""Build attestations from a whitelist, never by copying and deleting.

build_attestation() takes a display name and a WorkerSummary, never a Worker, so hours,
visa and shifts cannot reach it. Every output field is set explicitly.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from app import interfaces
from app.models import (
    FORBIDDEN_ATTESTATION_KEYS,
    Attestation,
    AttSource,
    DisclosureItem,
    Issuer,
    MonthAmount,
    PreviewResponse,
    Scope,
    SourceSummary,
    Subject,
    Tier,
    TimelineResponse,
    WorkerSummary,
)

FORBIDDEN_KEYS = FORBIDDEN_ATTESTATION_KEYS
RENTAL_SOURCE_FIELDS = ("label", "type", "tier", "evidence")

VALIDITY = timedelta(days=30)
FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def build_attestation(
    display_name: str,
    summary: WorkerSummary,
    scope: Scope,
    issued_at: datetime,
    att_id: str,
    issuer: Issuer,
) -> Attestation:
    """Unsigned attestation built field by field from a WorkerSummary.
    Lending adds monthly_series and per-source monthly_median. expires_at = issued_at + 30 days."""
    lending = scope == Scope.lending
    sources = [
        AttSource(
            label=s.label,
            type=s.type,
            tier=s.tier,
            evidence=list(s.evidence),
            monthly_median=s.monthly_median if lending else None,
        )
        for s in summary.sources
        if s.tier != Tier.D  # defensive: D is never attested
    ]
    series = (
        [MonthAmount(month=m.month, amount=m.amount) for m in summary.monthly_series]
        if lending and summary.monthly_series is not None
        else None
    )
    return Attestation(
        attestation_id=att_id,
        scope=scope,
        subject=Subject(display_name=display_name),
        issuer=issuer,
        period=summary.period,
        sources=sources,
        summary=summary.summary,
        monthly_series=series,
        issued_at=issued_at,
        expires_at=issued_at + VALIDITY,
    )


def disclosures(
    scope: Scope, display_name: str
) -> tuple[list[DisclosureItem], list[DisclosureItem]]:
    """(included, excluded) for the preview; see fixtures/preview.json."""
    included = [
        DisclosureItem(key="subject", label=f"Your display name ({display_name})"),
        DisclosureItem(key="sources", label="Income source names, types and evidence tiers"),
        DisclosureItem(key="monthly_income_range", label="Monthly income range"),
        DisclosureItem(key="monthly_median", label="Median monthly income"),
        DisclosureItem(key="coverage", label="Months with data (coverage)"),
        DisclosureItem(key="period", label="Period the proof covers"),
        DisclosureItem(key="issuer", label="Issuer, issue date and expiry date"),
    ]
    excluded = [
        DisclosureItem(key="hours", label="Hours and shifts", reason="never"),
        DisclosureItem(key="visa", label="Visa status", reason="never"),
        DisclosureItem(key="transactions", label="Individual transactions and bank deposits", reason="never"),
        DisclosureItem(
            key="checks",
            label="Integrity check results (for example, possible underpayment)",
            reason="never",
        ),
    ]
    scoped = [
        DisclosureItem(key="monthly_series", label="Income for each month"),
        DisclosureItem(key="source_amounts", label="Income from each source"),
    ]
    if scope == Scope.lending:
        included += scoped
    else:
        excluded += [d.model_copy(update={"reason": "scope"}) for d in scoped]
    return included, excluded


def _fixture_summary(worker_id: str) -> tuple[str, WorkerSummary]:
    """Mei's summary from fixtures, used until the data area is merged."""
    if worker_id != "mei":
        raise interfaces.WorkerNotFound(worker_id)
    timeline = TimelineResponse.model_validate_json((FIXTURES / "timeline.json").read_text())
    preview = PreviewResponse.model_validate_json((FIXTURES / "preview.json").read_text())
    sources = [
        SourceSummary(
            source_id=s.source_id, label=s.label, type=s.type, tier=s.tier, evidence=s.evidence
        )
        for s in timeline.sources
        if s.tier != Tier.D
    ]
    summary = WorkerSummary(
        period=timeline.period,
        sources=sources,
        summary=preview.attestation.summary,
        monthly_series=None,
    )
    return timeline.display_name, summary


def mei_summary(worker_id: str, scope: Scope) -> tuple[str, WorkerSummary]:
    """(display_name, WorkerSummary) via interfaces; falls back to fixtures only while the
    data area is unimplemented (NotImplementedError). Any other error propagates."""
    try:
        worker = interfaces.load_worker(worker_id)
        return worker.display_name, interfaces.summarize_worker(worker, scope)
    except NotImplementedError:
        return _fixture_summary(worker_id)
