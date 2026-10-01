"""Match income records to bank deposits."""

from datetime import timedelta

from app.models import BankDeposit, IncomeRecord, IncomeSource

_SUFFIXES = (" pty ltd", " pty", " ltd", " payroll", " payment")


def normalize(name: str) -> str:
    s = "".join(c for c in name.lower() if c.isalnum() or c == " ")
    for suffix in _SUFFIXES:
        s = s.replace(suffix, "")
    return " ".join(s.split())


def payer_name(source: IncomeSource) -> str:
    return source.source_id.replace("-", " ")


def match_deposit(
    record: IncomeRecord, deposits: list[BankDeposit], payer_name: str, fx_tolerance: float = 0.02
) -> BankDeposit | None:
    """AUD within $1 (overseas within 2%), dated paid_on..paid_on+3, payer name in description."""
    tol = int(record.net_cents * fx_tolerance) if record.original_currency else 100
    payer = normalize(payer_name)
    for d in deposits:
        if (
            abs(d.amount_cents - record.net_cents) <= tol
            and record.paid_on <= d.date <= record.paid_on + timedelta(days=3)
            and payer in normalize(d.description)
        ):
            return d
    return None


def match_all(
    records: list[IncomeRecord], deposits: list[BankDeposit], payer_names: dict[str, str]
) -> dict[str, BankDeposit]:
    """Map record_id -> matched deposit, each deposit used at most once."""
    remaining = list(deposits)
    matched: dict[str, BankDeposit] = {}
    for r in sorted(records, key=lambda r: (r.paid_on, r.record_id)):
        if r.source_id not in payer_names:
            continue
        d = match_deposit(r, remaining, payer_names[r.source_id])
        if d is not None:
            matched[r.record_id] = d
            remaining.remove(d)
    return matched
