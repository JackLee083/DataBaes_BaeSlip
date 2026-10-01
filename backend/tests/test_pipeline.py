"""Tier + matching pipeline on the real mei.json (BUILD_GUIDE 5.1-5.2)."""

import json
from pathlib import Path

from app.models import Evidence, TimelineRecord, TimelineSource
from app.services import loader
from app.services.tiers import TieredIncome, tier_worker

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _mei():
    return loader.load_worker("mei")


def test_every_non_cash_record_matched():
    w = _mei()
    result = tier_worker(w)
    assert isinstance(result, TieredIncome)
    assert len(result.deposit_of) == 47
    assert "inc_036" not in result.deposit_of
    assert len(result.records) == len(w.income)


def test_source_tiers_mei():
    tiers = {s.source_id: s.tier.value for s in tier_worker(_mei()).sources}
    assert tiers == {"abc-cafe": "A", "delivery-co": "B", "studio-sg": "C", "cash-tutoring": "D"}


def test_evidence_in_enum_order():
    result = tier_worker(_mei())
    studio = next(s for s in result.sources if s.source_id == "studio-sg")
    assert [e.value for e in studio.evidence] == ["invoice", "bank_deposit"]
    recs = [r for r in result.records if r.source_id == "studio-sg"]
    assert recs
    for r in recs:
        assert [e.value for e in r.evidence] == ["invoice", "bank_deposit"]
    order = list(Evidence)
    for r in result.records:
        assert r.evidence == sorted(set(r.evidence), key=order.index)


def test_distractor_deposits_unmatched():
    w = _mei()
    matched_ids = set(tier_worker(w).deposit_of.values())
    distractors = [
        d
        for d in w.bank_deposits
        if d.description in ("RENT REFUND", "TRANSFER FROM L CHEN")
        or (d.description == "ABC CAFE PAYROLL" and d.amount_cents == 8250)
    ]
    assert len(distractors) >= 3
    for d in distractors:
        assert d.deposit_id not in matched_ids


def test_unmatched_overseas_falls_to_d():
    w = _mei().model_copy(deep=True)
    rec = next(r for r in w.income if r.source_id == "studio-sg")
    matched = tier_worker(w).deposit_of[rec.record_id]
    w.bank_deposits = [d for d in w.bank_deposits if d.deposit_id != matched]
    result = tier_worker(w)
    assert rec.record_id not in result.deposit_of
    out = next(r for r in result.records if r.record_id == rec.record_id)
    assert out.tier.value == "D"
    studio = next(s for s in result.sources if s.source_id == "studio-sg")
    assert studio.tier.value == "D"


def test_input_worker_not_mutated():
    w = _mei()
    before = w.model_dump()
    tier_worker(w)
    assert w.model_dump() == before


def test_records_equal_timeline_fixture():
    fx = json.loads((FIXTURES / "timeline.json").read_text())
    result = tier_worker(_mei())
    want_recs = [TimelineRecord.model_validate(r).model_dump(mode="json") for r in fx["records"]]
    assert [r.model_dump(mode="json") for r in result.records] == want_recs
    want_src = [TimelineSource.model_validate(s).model_dump(mode="json") for s in fx["sources"]]
    assert [s.model_dump(mode="json") for s in result.sources] == want_src
