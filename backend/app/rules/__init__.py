"""Integrity rules R1-R4 (worker only). Owner: rules (B4-B7).
interfaces.run_all_checks delegates here."""

from app.config import Config
from app.models import Check, Worker
from app.rules import r1_min_wage, r2_delivery, r3_super, r4_visa_hours


def run_all_checks(worker: Worker, cfg: Config) -> list[Check]:
    """Run R1, R2, R3, R4 in that fixed order and concatenate their results."""
    checks: list[Check] = []
    for rule in (r1_min_wage, r2_delivery, r3_super, r4_visa_hours):
        checks.extend(rule.run(worker, cfg))
    return checks
