"""R2 delivery minimum per engaged hour.

Uses engaged minutes only (never online minutes). A payout week with no engaged
minutes, or engaged minutes with no payout row, cannot be verified and emits nothing.
"""

from __future__ import annotations

from datetime import timedelta

from app.config import Config
from app.models import Check, Severity, SourceType, Worker


def run(worker: Worker, cfg: Config) -> list[Check]:
    platform_sources = {
        source.source_id: source.label
        for source in worker.sources
        if source.type == SourceType.platform
    }
    checks: list[Check] = []

    for payout in sorted(worker.platform_payouts, key=lambda p: (p.week_start, p.source_id)):
        if payout.source_id not in platform_sources:
            continue
        week_end = payout.week_start + timedelta(days=6)
        engaged_minutes = sum(
            day.engaged_minutes
            for day in worker.platform_days
            if day.source_id == payout.source_id and payout.week_start <= day.date <= week_end
        )
        if engaged_minutes <= 0:
            continue

        # Round half up with integers only.
        expected = (2 * engaged_minutes * cfg.delivery_min_per_engaged_hour_cents + 60) // 120
        difference = expected - payout.amount_cents
        if difference <= cfg.tolerance_cents:
            continue

        checks.append(
            Check(
                check_id=f"r2-{payout.source_id}-{payout.week_start.isoformat()}",
                rule="R2",
                severity=Severity.review,
                title="Delivery pay may be below the minimum for engaged time",
                period_start=payout.week_start,
                period_end=week_end,
                expected_cents=expected,
                actual_cents=payout.amount_cents,
                difference_cents=difference,
                facts={
                    "source_id": payout.source_id,
                    "source_label": platform_sources[payout.source_id],
                    "engaged_minutes": engaged_minutes,
                    "engaged_hours": engaged_minutes / 60,
                    "min_per_engaged_hour_cents": cfg.delivery_min_per_engaged_hour_cents,
                    "payout_cents": payout.amount_cents,
                    "paid_on": payout.paid_on,
                    "limitations": [
                        "Platform exports may not include engaged time.",
                        "How the minimum is calculated should be checked against the FWC decision.",
                    ],
                },
                possible_explanations=[
                    "The platform may count engaged time differently.",
                    "Tips or adjustments may be paid in a different week.",
                    "The minimum may differ for your vehicle type.",
                ],
                next_steps=[
                    "Download your platform earnings and trip history for this week.",
                    "Ask the platform how this week's pay was calculated.",
                    "The Fair Work Ombudsman or a union can help you check the minimum.",
                ],
            )
        )

    return checks
