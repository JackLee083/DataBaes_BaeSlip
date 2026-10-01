from datetime import date, timedelta

from app.models import BankDeposit, Evidence, IncomeRecord, IncomeSource, SourceType
from app.services.matching import match_all, match_deposit, normalize, payer_name

PAID = date(2026, 3, 10)


def rec(rid="inc_001", source="abc-cafe", net=100000, paid=PAID, **kw):
    return IncomeRecord(
        record_id=rid,
        source_id=source,
        period_start=paid - timedelta(days=14),
        period_end=paid - timedelta(days=1),
        gross_cents=net,
        net_cents=net,
        paid_on=paid,
        evidence=[Evidence.self_reported],
        **kw,
    )


def dep(did="d1", d=PAID, desc="ABC CAFE PAYROLL", amt=100000):
    return BankDeposit(deposit_id=did, date=d, description=desc, amount_cents=amt)


def test_normalize_strips_suffixes():
    assert normalize("ABC CAFE PAYROLL") == "abc cafe"
    assert normalize("DELIVERY CO PTY LTD PAYMENT") == "delivery co"
    assert normalize("  Abc-Cafe,  Pty  ") == "abccafe"
    assert normalize("abc cafe") == "abc cafe"


def test_real_descriptions():
    assert match_deposit(rec(), [dep()], "abc cafe")
    r = rec(source="delivery-co")
    assert match_deposit(r, [dep(desc="DELIVERY CO PTY LTD PAYMENT")], "delivery co")
    r = rec(source="studio-sg", net=500000, original_currency="SGD", original_amount_cents=1)
    assert match_deposit(r, [dep(desc="STUDIO SG PTE LTD INTL TFR", amt=500000)], "studio sg")
    for desc in ("RENT REFUND", "TRANSFER FROM L CHEN"):
        assert match_deposit(rec(), [dep(desc=desc)], "abc cafe") is None


def test_aud_within_1_dollar():
    assert match_deposit(rec(), [dep(amt=100100)], "abc cafe")
    assert match_deposit(rec(), [dep(amt=99900)], "abc cafe")


def test_aud_off_by_2_dollars_fails():
    assert match_deposit(rec(), [dep(amt=100200)], "abc cafe") is None


def test_fx_within_2_percent():
    r = rec(net=500000, original_currency="SGD", original_amount_cents=1)
    assert match_deposit(r, [dep(desc="STUDIO SG", amt=510000)], "studio sg")
    assert match_deposit(r, [dep(desc="STUDIO SG", amt=490000)], "studio sg")
    assert match_deposit(r, [dep(desc="STUDIO SG", amt=510001)], "studio sg") is None
    assert match_deposit(r, [dep(desc="STUDIO SG", amt=489999)], "studio sg") is None


def test_date_window():
    for delta in (0, 3):
        assert match_deposit(rec(), [dep(d=PAID + timedelta(days=delta))], "abc cafe")
    for delta in (-1, 4):
        assert match_deposit(rec(), [dep(d=PAID + timedelta(days=delta))], "abc cafe") is None


def test_name_mismatch_fails():
    assert match_deposit(rec(), [dep(desc="OTHER CO PAYROLL")], "abc cafe") is None


def test_deposit_used_once():
    records = [rec("inc_001"), rec("inc_002")]
    result = match_all(records, [dep()], {"abc-cafe": "abc cafe"})
    assert list(result) == ["inc_001"]
    assert result["inc_001"].deposit_id == "d1"


def test_payer_name_from_source_id():
    s = IncomeSource(source_id="abc-cafe", label="Hospitality", type=SourceType.employment)
    assert payer_name(s) == "abc cafe"


def test_match_all_skips_unknown_sources():
    records = [rec("inc_001", source="cash-tips"), rec("inc_002")]
    result = match_all(records, [dep()], {"abc-cafe": "abc cafe"})
    assert set(result) == {"inc_002"}


def test_match_all_paid_on_order():
    late = rec("inc_001", paid=PAID + timedelta(days=1))
    early = rec("inc_002", paid=PAID)
    deps = [dep("d1", d=PAID), dep("d2", d=PAID + timedelta(days=1))]
    result = match_all([late, early], deps, {"abc-cafe": "abc cafe"})
    assert result["inc_002"].deposit_id == "d1"
    assert result["inc_001"].deposit_id == "d2"
