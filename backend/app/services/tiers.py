"""Evidence tiers (BUILD_GUIDE 5.1). Owner: data (B2)."""

from dataclasses import dataclass

from app.models import Evidence, Tier, TimelineRecord, TimelineSource, Worker
from app.services import matching

_EVIDENCE_TIER: dict[Evidence, Tier] = {
    Evidence.stp_income_statement: Tier.A,
    Evidence.notice_of_assessment: Tier.A,
    Evidence.platform_statement: Tier.B,
    Evidence.payer_confirmed_invoice: Tier.B,
    Evidence.bank_deposit: Tier.C,
    Evidence.self_reported: Tier.D,
}  # Evidence.invoice has no tier on its own

_ORDER = [Tier.A, Tier.B, Tier.C, Tier.D]  # strongest to weakest


def record_tier(evidence: list[Evidence]) -> Tier:
    """The strongest tier among the record's evidence; D if none."""
    tiers = [_EVIDENCE_TIER[Evidence(e)] for e in evidence if Evidence(e) in _EVIDENCE_TIER]
    return min(tiers, key=_ORDER.index, default=Tier.D)


def source_tier(record_tiers: list[Tier]) -> Tier:
    """The weakest tier among the source's records (conservative); D if none."""
    return max((Tier(t) for t in record_tiers), key=_ORDER.index, default=Tier.D)


@dataclass(frozen=True)
class TieredIncome:
    records: list[TimelineRecord]
    sources: list[TimelineSource]
    deposit_of: dict[str, str]  # record_id -> deposit_id


def _in_order(kinds) -> list[Evidence]:
    order = list(Evidence)
    return sorted({Evidence(k) for k in kinds}, key=order.index)


def tier_worker(worker: Worker) -> TieredIncome:
    """Match deposits, tier every record and source. Does not mutate the worker."""
    matches = matching.match_all(
        worker.income,
        worker.bank_deposits,
        {s.source_id: matching.payer_name(s) for s in worker.sources},
    )
    records: list[TimelineRecord] = []
    for r in sorted(worker.income, key=lambda r: (r.paid_on, r.record_id)):
        kinds = list(r.evidence)
        if r.record_id in matches:
            kinds.append(Evidence.bank_deposit)
        evidence = _in_order(kinds)
        records.append(
            TimelineRecord(
                **r.model_dump(exclude={"evidence"}),
                evidence=evidence,
                tier=record_tier(evidence),
            )
        )
    sources = []
    for s in worker.sources:
        own = [r for r in records if r.source_id == s.source_id]
        sources.append(
            TimelineSource(
                source_id=s.source_id,
                label=s.label,
                type=s.type,
                tier=source_tier([r.tier for r in own]),
                evidence=_in_order(e for r in own for e in r.evidence),
            )
        )
    return TieredIncome(records, sources, {rid: d.deposit_id for rid, d in matches.items()})
