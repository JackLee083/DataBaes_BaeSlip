"""Attestations are built from a whitelist; nothing else can leak in."""

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app import interfaces
from app.models import (
    FORBIDDEN_ATTESTATION_KEYS,
    Coverage,
    Evidence,
    Issuer,
    MoneyRange,
    MonthAmount,
    Period,
    Scope,
    SourceSummary,
    SourceType,
    Summary,
    Tier,
    Worker,
    WorkerSummary,
)
from app.services import attestation

REPO = Path(__file__).resolve().parents[2]
PREVIEW = json.loads((REPO / "fixtures" / "preview.json").read_text())
ISSUER = Issuer(**PREVIEW["attestation"]["issuer"])
ISSUED = datetime(2026, 9, 29, 10, 0, tzinfo=timezone(timedelta(hours=10)))


def make_summary() -> WorkerSummary:
    return WorkerSummary(
        period=Period(start=date(2026, 4, 1), end=date(2026, 9, 30)),
        sources=[
            SourceSummary(
                source_id="a", label="Cafe", type=SourceType.employment, tier=Tier.A,
                evidence=[Evidence.stp_income_statement, Evidence.bank_deposit],
                monthly_median=1500,
            ),
            SourceSummary(
                source_id="b", label="Platform", type=SourceType.platform, tier=Tier.B,
                evidence=[Evidence.platform_statement], monthly_median=900,
            ),
            SourceSummary(
                source_id="d", label="Cash tutoring", type=SourceType.cash, tier=Tier.D,
                evidence=[Evidence.self_reported], monthly_median=300,
            ),
        ],
        summary=Summary(
            monthly_income_range=MoneyRange(low=2300, high=3100),
            monthly_median=2700,
            coverage=Coverage(months_with_data=6, months_in_period=6),
        ),
        monthly_series=[MonthAmount(month="2026-04", amount=2300),
                        MonthAmount(month="2026-05", amount=3100)],
    )


def build(scope: Scope, summary: WorkerSummary | None = None):
    return attestation.build_attestation(
        "Mei L.", summary or make_summary(), scope, ISSUED, "att_x", ISSUER
    )


def walk_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_keys(v)


@pytest.mark.parametrize("scope", [Scope.rental, Scope.lending])
def test_no_forbidden_keys(scope):
    dumped = build(scope).model_dump(mode="json", exclude_none=True)
    assert not set(walk_keys(dumped)) & FORBIDDEN_ATTESTATION_KEYS


def test_rental_has_no_monthly_series_or_source_median():
    dumped = build(Scope.rental).model_dump(mode="json", exclude_none=True)
    assert "monthly_series" not in dumped
    assert all("monthly_median" not in s for s in dumped["sources"])
    assert dumped["summary"]["monthly_median"] == 2700  # summary median stays


def test_lending_has_series_and_source_medians():
    att = build(Scope.lending)
    assert [m.amount for m in att.monthly_series] == [2300, 3100]
    assert [s.monthly_median for s in att.sources] == [1500, 900]


def test_d_sources_dropped():
    for scope in (Scope.rental, Scope.lending):
        att = build(scope)
        assert [s.label for s in att.sources] == ["Cafe", "Platform"]
        assert all(s.tier != Tier.D for s in att.sources)


def test_expires_after_30_days():
    att = build(Scope.rental)
    assert att.expires_at - att.issued_at == timedelta(days=30)
    assert att.signature is None


def _force_fallback(monkeypatch):
    def boom(_):
        raise NotImplementedError

    monkeypatch.setattr(interfaces, "load_worker", boom)


def test_matches_preview_fixture(monkeypatch):
    _force_fallback(monkeypatch)
    name, summary = attestation.mei_summary("mei", Scope.rental)
    att = attestation.build_attestation(name, summary, Scope.rental, ISSUED, "preview", ISSUER)
    assert att.model_dump(mode="json", exclude_none=True) == PREVIEW["attestation"]


def test_disclosures_match_preview_fixture():
    included, excluded = attestation.disclosures(Scope.rental, "Mei L.")
    assert [i.model_dump(mode="json", exclude_none=True) for i in included] == PREVIEW["included"]
    assert [i.model_dump(mode="json", exclude_none=True) for i in excluded] == PREVIEW["excluded"]


def test_disclosure_labels_are_english():
    included, excluded = attestation.disclosures(Scope.rental, "Mei L.")
    labels = {i.key: i.label for i in included + excluded}
    assert labels["subject"] == "Your display name (Mei L.)"
    assert labels["hours"] == "Hours and shifts"
    assert labels["visa"] == "Visa status"
    assert all(label.isascii() for label in labels.values())


def test_disclosures_lending_moves_amounts_to_included():
    included, excluded = attestation.disclosures(Scope.lending, "Mei L.")
    inc = {i.key: i for i in included}
    assert inc["monthly_series"].label == "Income for each month"
    assert inc["source_amounts"].label == "Income from each source"
    assert inc["monthly_series"].reason is None
    assert [e.key for e in excluded] == ["hours", "visa", "transactions", "checks"]
    assert all(e.reason == "never" for e in excluded)


def test_fallback_only_on_not_implemented(monkeypatch):
    def not_found(_):
        raise interfaces.WorkerNotFound("x")

    monkeypatch.setattr(interfaces, "load_worker", not_found)
    with pytest.raises(interfaces.WorkerNotFound):
        attestation.mei_summary("mei", Scope.rental)

    def runtime(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(interfaces, "load_worker", runtime)
    with pytest.raises(RuntimeError):
        attestation.mei_summary("mei", Scope.rental)

    worker = Worker(
        worker_id="w", display_name="Real W.", language="en", visa=None,
        today=date(2026, 9, 29), period_start=date(2026, 4, 1), period_end=date(2026, 9, 30),
        sources=[], income=[], shifts=[], platform_days=[], platform_payouts=[],
        super_contributions=[], bank_deposits=[],
    )
    summary = make_summary()
    monkeypatch.setattr(interfaces, "load_worker", lambda _id: worker)
    monkeypatch.setattr(interfaces, "summarize_worker", lambda w, s: summary)
    assert attestation.mei_summary("w", Scope.rental) == ("Real W.", summary)


def test_fallback_unknown_worker(monkeypatch):
    _force_fallback(monkeypatch)
    with pytest.raises(interfaces.WorkerNotFound):
        attestation.mei_summary("nobody", Scope.rental)
