"""Rule parameters and environment settings. Owner: core.

Rules receive a Config (`run(worker, cfg)`); nothing else should hard-code these values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    # R1: national minimum wage, casual rate. Only for workers not covered by an award
    # or agreement; the real award may differ.
    min_casual_hourly_cents: int = 3305
    # R2: delivery minimum per engaged hour, bicycle or e-bike. ⚠️ check against FWC text.
    delivery_min_per_engaged_hour_cents: int = 3130
    tolerance_cents: int = 100
    # R3: Payday Super deadline; the demo skips weekends only, not public holidays.
    super_deadline_business_days: int = 7
    # R4: student visa work limit.
    visa_limit_hours: int = 48
    visa_warn_hours: int = 44
    visa_window_days: int = 14
    # Demo course break (no work limit); production would read the academic calendar.
    course_breaks: tuple[tuple[date, date], ...] = ((date(2026, 6, 20), date(2026, 7, 26)),)

    # Attestations
    attestation_ttl_days: int = 30
    issuer_id: str = "baeslip-demo"
    issuer_name: str = "BaeSlip Demo Issuer"
    key_id: str = "k1"

    # Environment
    public_web_url: str = field(
        default_factory=lambda: os.environ.get("PUBLIC_WEB_URL", "http://localhost:5173")
    )
    issuer_key_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("ISSUER_KEY_PATH", BACKEND_DIR / "keys" / "issuer_ed25519.pem")
        )
    )
    store_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("STORE_PATH", BACKEND_DIR / "app" / "data" / "attestations.json")
        )
    )


def get_config() -> Config:
    return Config()
