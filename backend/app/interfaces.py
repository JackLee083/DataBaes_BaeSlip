"""Cross-area function signatures (contract). Owner: contract (Claude-1).

Areas call each other only through this module. Each function delegates to the
owning area's module, which starts as a stub raising NotImplementedError; the owner
replaces that stub, and this file never needs to change. Until then, callers test
against fixtures/*.json.
"""

from __future__ import annotations

from app.config import Config
from app.models import (
    Check,
    ExplainResponse,
    Scope,
    TimelineResponse,
    Worker,
    WorkerSummary,
)


class WorkerNotFound(LookupError):
    """Raised by load_worker() for an unknown worker_id; routers map it to HTTP 404."""


def load_worker(worker_id: str) -> Worker:
    """Owner: data (services/loader.py, ticket B1).

    Load backend/app/data/<worker_id>.json as a validated Worker. Raw evidence lists
    never contain bank_deposit; matching adds it later.
    Raises WorkerNotFound if there is no such worker.
    """
    from app.services import loader

    return loader.load_worker(worker_id)


def build_timeline(worker: Worker) -> TimelineResponse:
    """Owner: data (services/summary.py, tickets B2, B3, B12).

    Match income to bank deposits (adding bank_deposit evidence only on a match),
    attach record and source tiers, and total each month. Returns the body of
    GET /workers/{worker_id}/timeline; see fixtures/timeline.json.
    """
    from app.services import summary

    return summary.build_timeline(worker)


def summarize_worker(worker: Worker, scope: Scope) -> WorkerSummary:
    """Owner: data (services/summary.py, tickets B2, B3).

    Monthly net income by paid_on month, A-C tiers only (D is never counted), then
    range, median and coverage in integer dollars. Sources: only those with tier A-C.
    For scope=rental, monthly_series and each source's monthly_median are None;
    for scope=lending they are filled.
    """
    from app.services import summary

    return summary.summarize_worker(worker, scope)


def run_all_checks(worker: Worker, cfg: Config | None = None) -> list[Check]:
    """Owner: rules (rules/__init__.py, tickets B4-B7).

    Run R1-R4 and return every Check, worker-only. cfg defaults to get_config().
    Money and hours are computed here, never by AI. See fixtures/checks.json.
    """
    from app import rules
    from app.config import get_config

    return rules.run_all_checks(worker, cfg or get_config())


def explain_check(check: Check, language: str) -> ExplainResponse:
    """Owner: rules (explain.py, ticket B13).

    Plain-language explanation of one Check in `language`. The AI only rewords the
    Check's facts and computes nothing; with no API key, a network error or a refusal
    it falls back to the template (source="template"). See fixtures/explain.json.
    """
    from app import explain

    return ExplainResponse.model_validate(explain.explain(check, language))
