from app.models import Evidence as E
from app.models import Tier
from app.services.tiers import record_tier, source_tier


def test_a_plus_c_is_a():
    assert record_tier([E.stp_income_statement, E.bank_deposit]) == Tier.A
    assert record_tier([E.notice_of_assessment]) == Tier.A


def test_invoice_only_is_d():
    assert record_tier([E.invoice]) == Tier.D


def test_invoice_plus_bank_is_c():
    assert record_tier([E.invoice, E.bank_deposit]) == Tier.C


def test_platform_is_b():
    assert record_tier([E.platform_statement]) == Tier.B
    assert record_tier([E.payer_confirmed_invoice, E.bank_deposit]) == Tier.B


def test_self_reported_is_d():
    assert record_tier([E.self_reported]) == Tier.D


def test_source_tier_takes_weakest():
    assert source_tier([Tier.A, Tier.C, Tier.B]) == Tier.C
    assert source_tier([Tier.A, Tier.A]) == Tier.A
    assert source_tier([Tier.B, Tier.D]) == Tier.D


def test_empty_is_d():
    assert record_tier([]) == Tier.D
    assert source_tier([]) == Tier.D
