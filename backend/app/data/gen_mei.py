"""Deterministic generator for app/data/mei.json (Mei, the demo worker).

Run from backend/:  python -m app.data.gen_mei
Stdlib only; never imported at runtime (the loader reads the committed JSON).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "mei.json"
D = timedelta(days=1)

SOURCES = [
    ("abc-cafe", "Hospitality (casual)", "employment"),
    ("delivery-co", "Food delivery platform", "platform"),
    ("studio-sg", "Overseas design contracts", "overseas_contract"),
    ("cash-tutoring", "Private tutoring (cash)", "cash"),
]
EVIDENCE = {
    "abc-cafe": "stp_income_statement",
    "delivery-co": "platform_statement",
    "studio-sg": "invoice",
    "cash-tutoring": "self_reported",
}
DEPOSIT_DESC = {
    "abc-cafe": "ABC CAFE PAYROLL",
    "delivery-co": "DELIVERY CO PTY LTD PAYMENT",
    "studio-sg": "STUDIO SG PTE LTD INTL TFR",
}
SOURCE_ORDER = {s[0]: i for i, s in enumerate(SOURCES)}

MIN_CASUAL_CENTS = 3305
FIRST_CAFE_START = date(2026, 3, 31)
LAST_CAFE_START = date(2026, 9, 15)
CAFE_HOURS = {date(2026, 5, 12): 18, date(2026, 6, 23): 22, date(2026, 7, 7): 22}
CAFE_GROSS_OVERRIDE = {date(2026, 9, 1): 44000}  # R1 trigger
SUPER_LATE = {date(2026, 9, 2): date(2026, 9, 8), date(2026, 9, 16): date(2026, 9, 28)}

FIRST_WEEK = date(2026, 3, 30)
LAST_WEEK = date(2026, 9, 21)
WEEK_ENGAGED = {date(2026, 4, 27): 300, date(2026, 5, 4): 300, date(2026, 5, 11): 300,
                date(2026, 5, 18): 300, date(2026, 8, 31): 240, date(2026, 9, 14): 240,
                date(2026, 9, 7): 540}
WEEK_PAYOUT = {360: 19800, 300: 16500, 240: 13200, 540: 25000}

# (period_start, period_end, paid_on, net AUD cents, original USD cents), per fixtures/timeline.json
STUDIO = [
    ("2026-04-01", "2026-04-14", "2026-04-17", 33600, 22400),
    ("2026-05-01", "2026-05-15", "2026-05-19", 38410, 25600),
    ("2026-05-18", "2026-06-01", "2026-06-05", 35000, 23300),
    ("2026-06-08", "2026-06-22", "2026-06-26", 31800, 21200),
    ("2026-06-23", "2026-07-07", "2026-07-10", 42000, 28000),
    ("2026-07-08", "2026-07-21", "2026-07-24", 43380, 28900),
    ("2026-07-27", "2026-08-10", "2026-08-14", 30800, 20500),
    ("2026-08-17", "2026-08-31", "2026-09-04", 48000, 32000),
    ("2026-09-02", "2026-09-18", "2026-09-22", 48700, 32500),
]

PLANNED = [("2026-09-30", 8), ("2026-10-01", 8), ("2026-10-03", 6), ("2026-10-04", 4),
           ("2026-10-05", 4), ("2026-10-07", 6), ("2026-10-09", 4), ("2026-10-10", 6),
           ("2026-10-11", 4)]


def iso(d: date) -> str:
    return d.isoformat()


def _cafe(income, shifts, supers):
    start = FIRST_CAFE_START
    while start <= LAST_CAFE_START:
        end = start + 13 * D
        hours = CAFE_HOURS.get(start, 20)
        for offset in (1, 4, 8, 11):  # Wed, Sat, Wed, Sat (period starts on a Tuesday)
            shifts.append({"date": iso(start + offset * D), "hours": hours / 4,
                           "source_id": "abc-cafe", "planned": False})
        paid = end + 2 * D
        if start < LAST_CAFE_START:  # the last period is not paid until 9/30
            gross = CAFE_GROSS_OVERRIDE.get(start, hours * MIN_CASUAL_CENTS)
            income.append(dict(source_id="abc-cafe", period_start=start, period_end=end,
                               gross=gross, net=gross, paid_on=paid, orig=None))
            supers.append({"source_id": "abc-cafe", "payday": iso(paid),
                           "amount_cents": round(gross * 0.12),
                           "received_on": iso(SUPER_LATE.get(paid, paid + 6 * D))})
        start += 14 * D
    for day, h in PLANNED:
        shifts.append({"date": day, "hours": float(h), "source_id": "abc-cafe", "planned": True})


def _delivery(income, days, payouts):
    week = FIRST_WEEK
    while week <= LAST_WEEK:
        engaged = WEEK_ENGAGED.get(week, 360)
        payout = WEEK_PAYOUT[engaged]
        per_day = engaged // 3
        share = payout // 3
        for i, off in enumerate((0, 3, 4)):  # Mon, Thu, Fri
            gross = share if i < 2 else payout - 2 * share
            days.append({"date": iso(week + off * D), "source_id": "delivery-co",
                         "engaged_minutes": per_day, "online_minutes": per_day + 10,
                         "gross_cents": gross})
        paid = week + 7 * D
        payouts.append({"source_id": "delivery-co", "week_start": iso(week),
                        "amount_cents": payout, "paid_on": iso(paid)})
        income.append(dict(source_id="delivery-co", period_start=week, period_end=week + 6 * D,
                           gross=payout, net=payout, paid_on=paid, orig=None))
        week += 7 * D


def _studio(income, shifts):
    for a, b, paid, aud, usd in STUDIO:
        income.append(dict(source_id="studio-sg", period_start=date.fromisoformat(a),
                           period_end=date.fromisoformat(b), gross=aud, net=aud,
                           paid_on=date.fromisoformat(paid), orig=usd))
    day = date(2026, 3, 29)
    while day <= date(2026, 9, 27):  # Sundays
        shifts.append({"date": iso(day), "hours": 3.0, "source_id": "studio-sg", "planned": False})
        day += 7 * D


def build() -> dict:
    income_raw, shifts, days, payouts, supers = [], [], [], [], []
    _cafe(income_raw, shifts, supers)
    _delivery(income_raw, days, payouts)
    _studio(income_raw, shifts)
    income_raw.append(dict(source_id="cash-tutoring", period_start=date(2026, 8, 15),
                           period_end=date(2026, 8, 15), gross=6000, net=6000,
                           paid_on=date(2026, 8, 15), orig=None))
    income_raw.sort(key=lambda r: (r["paid_on"], SOURCE_ORDER[r["source_id"]], r["period_start"]))

    income, deposits = [], []
    for i, r in enumerate(income_raw, start=1):
        rec = {
            "record_id": f"inc_{i:03d}",
            "source_id": r["source_id"],
            "period_start": iso(r["period_start"]),
            "period_end": iso(r["period_end"]),
            "gross_cents": r["gross"],
            "net_cents": r["net"],
            "paid_on": iso(r["paid_on"]),
            "evidence": [EVIDENCE[r["source_id"]]],
            "currency": "AUD",
        }
        if r["orig"] is not None:
            rec["original_amount_cents"] = r["orig"]
            rec["original_currency"] = "USD"
        income.append(rec)
        if r["source_id"] in DEPOSIT_DESC:
            lag = 1 if r["source_id"] == "studio-sg" else 0
            deposits.append((r["paid_on"] + lag * D, DEPOSIT_DESC[r["source_id"]], r["net"]))
    deposits += [
        (date(2026, 5, 6), "RENT REFUND", 12000),
        (date(2026, 6, 3), "ABC CAFE PAYROLL", 8250),
        (date(2026, 7, 15), "TRANSFER FROM L CHEN", 5000),
    ]
    deposits.sort(key=lambda d: (d[0], d[1]))
    bank = [{"deposit_id": f"dep_{i:03d}", "date": iso(d), "description": desc, "amount_cents": amt}
            for i, (d, desc, amt) in enumerate(deposits, start=1)]

    shifts.sort(key=lambda s: (s["date"], s["source_id"]))
    return {
        "worker_id": "mei",
        "display_name": "Mei L.",
        "language": "en",
        "visa": "500",
        "today": "2026-09-29",
        "period_start": "2026-04-01",
        "period_end": "2026-09-30",
        "sources": [{"source_id": s, "label": l, "type": t} for s, l, t in SOURCES],
        "income": income,
        "shifts": shifts,
        "platform_days": days,
        "platform_payouts": payouts,
        "super_contributions": supers,
        "bank_deposits": bank,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
