"""BaeSlip contract: Pydantic models shared by every area.

Owner: contract (Claude-1). Frozen after TN0. To change anything here, follow
docs/AGENT_HANDBOOK.md section 2 ("Contract changes").

Conventions
- Internal money is integer cents (`*_cents`). Attestation money is integer dollars.
- Dates are ISO `YYYY-MM-DD`; datetimes are ISO 8601 with an offset.
- Every model forbids unknown keys, so a typo in mock data or a leaked field fails loudly.
- Attestation JSON on the wire omits null optional fields (`model_dump(mode="json",
  exclude_none=True)`). The signature covers exactly that form, so every API that
  returns an attestation must serialise it the same way.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

SPEC_VERSION = "0.1"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Enums -------------------------------------------------------------------------


class Tier(str, Enum):
    """Evidence tier. A: reported to government by a third party. B: confirmed by the
    payer. C: matched to a bank deposit. D: self-reported only."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


class SourceType(str, Enum):
    employment = "employment"
    platform = "platform"
    contract = "contract"
    overseas_contract = "overseas_contract"
    cash = "cash"


class Evidence(str, Enum):
    """Kinds of evidence. Declaration order is the canonical display order: a
    source-level evidence list is the set of kinds on its records, sorted in this order."""

    stp_income_statement = "stp_income_statement"  # -> A
    notice_of_assessment = "notice_of_assessment"  # -> A
    platform_statement = "platform_statement"  # -> B
    payer_confirmed_invoice = "payer_confirmed_invoice"  # -> B
    invoice = "invoice"  # no tier on its own
    bank_deposit = "bank_deposit"  # -> C; only added after a successful match
    self_reported = "self_reported"  # -> D


class Scope(str, Enum):
    """Disclosure scope. Only `rental` is served by the API; `lending` is spec-only."""

    rental = "rental"
    lending = "lending"


class Severity(str, Enum):
    info = "info"
    review = "review"
    warning = "warning"


class AttestationStatus(str, Enum):
    valid = "valid"
    expired = "expired"
    revoked = "revoked"
    not_found = "not_found"


# Keys that must never appear anywhere in an attestation (MVP_v2 principle 6).
FORBIDDEN_ATTESTATION_KEYS = frozenset(
    {
        "hours",
        "shifts",
        "visa",
        "transactions",
        "bank_deposits",
        "checks",
        "roster",
        "engaged_minutes",
        "online_minutes",
        "description",
    }
)


# --- Internal data (never leaves the issuer; input to rules and summary) -----------


class IncomeSource(Strict):
    source_id: str  # "abc-cafe"
    label: str  # "Hospitality (casual)"
    type: SourceType


class IncomeRecord(Strict):
    record_id: str  # "inc_001"
    source_id: str
    period_start: date
    period_end: date
    gross_cents: int
    net_cents: int  # the amount actually deposited; the summary uses this
    paid_on: date
    evidence: list[Evidence]
    currency: str = "AUD"
    original_amount_cents: int | None = None  # overseas income in its original currency
    original_currency: str | None = None


class WorkShift(Strict):
    """A rostered, clocked or self-logged shift. planned=True means a future shift."""

    date: date
    hours: float
    source_id: str
    planned: bool = False


class PlatformDay(Strict):
    date: date
    source_id: str
    engaged_minutes: int  # order accepted to delivered, including waiting at the venue
    online_minutes: int  # logged in; always >= engaged_minutes
    gross_cents: int


class PlatformPayout(Strict):
    source_id: str
    week_start: date  # a Monday; the week runs Monday to Sunday
    amount_cents: int
    paid_on: date


class SuperContribution(Strict):
    source_id: str
    payday: date  # the payday this contribution belongs to
    amount_cents: int
    received_on: date | None  # None = not received yet


class BankDeposit(Strict):
    deposit_id: str
    date: date
    description: str  # "ABC CAFE PAYROLL"
    amount_cents: int


class Worker(Strict):
    """Shape of backend/app/data/<worker_id>.json."""

    worker_id: str
    display_name: str  # "Mei L."
    language: str  # "en"
    visa: str | None  # "500"; rules engine only, never in an attestation
    today: date  # the demo's "today", fixed at 2026-09-29
    period_start: date
    period_end: date
    sources: list[IncomeSource]
    income: list[IncomeRecord]
    shifts: list[WorkShift]
    platform_days: list[PlatformDay]
    platform_payouts: list[PlatformPayout]
    super_contributions: list[SuperContribution]
    bank_deposits: list[BankDeposit]


# --- Integrity checks (worker only; never in an attestation) ------------------------


class Check(Strict):
    """Result of one integrity rule. Shown only to the worker.

    check_id: `r<n>-<source_id>-<period_start>`, e.g. "r1-abc-cafe-2026-09-01";
    R4 spans every source, so it uses `r4-all-<window_start>`.
    title may only say "may", "needs review" or "unable to verify"; never
    "violated", "stole" or "illegal".
    """

    check_id: str
    rule: Literal["R1", "R2", "R3", "R4"]
    severity: Severity
    title: str
    period_start: date
    period_end: date
    expected_cents: int | None = None
    actual_cents: int | None = None
    difference_cents: int | None = None
    facts: dict[str, Any]  # the raw numbers used, for the UI and the AI explanation
    possible_explanations: list[str]
    next_steps: list[str]


# --- Attestation (public; signed) --------------------------------------------------


class Subject(Strict):
    display_name: str


class Issuer(Strict):
    issuer_id: str
    name: str
    key_id: str  # matches a key in /.well-known/baeslip-keys.json


class Period(Strict):
    start: date
    end: date


class AttSource(Strict):
    label: str
    type: SourceType
    tier: Tier
    evidence: list[Evidence]
    monthly_median: int | None = None  # integer dollars; lending scope only


class MoneyRange(Strict):
    low: int  # integer dollars
    high: int


class Coverage(Strict):
    months_with_data: int
    months_in_period: int


class Summary(Strict):
    currency: str = "AUD"
    monthly_income_range: MoneyRange
    monthly_median: int  # integer dollars
    coverage: Coverage


class MonthAmount(Strict):
    month: str  # "2026-04"
    amount: int  # integer dollars


class Signature(Strict):
    alg: Literal["Ed25519"] = "Ed25519"
    value: str  # base64 of the Ed25519 signature over canonical JSON of everything else


class Attestation(Strict):
    """BaeSlip income attestation, spec 0.1.

    Signed content: the whole object except `signature`, as canonical JSON (keys
    sorted, no whitespace, UTF-8, null optional fields omitted), signed with Ed25519.
    Status (valid / expired / revoked) is not signed; the issuer reports it live.
    Never contains hours, visa status, individual transactions or integrity-check results.
    """

    spec_version: Literal["0.1"] = SPEC_VERSION
    attestation_id: str
    scope: Scope
    subject: Subject
    issuer: Issuer
    period: Period
    sources: list[AttSource]
    summary: Summary
    monthly_series: list[MonthAmount] | None = None  # lending scope only
    issued_at: datetime
    expires_at: datetime  # issued_at + 30 days
    signature: Signature | None = None  # absent only in previews


def attestation_schema() -> dict[str, Any]:
    """The JSON Schema committed as schema/attestation.schema.json."""
    return {"$schema": JSON_SCHEMA_DIALECT, **Attestation.model_json_schema()}


# --- Cross-area return types (see interfaces.py) -----------------------------------


class SourceSummary(Strict):
    source_id: str
    label: str
    type: SourceType
    tier: Tier  # the weakest tier among the source's records
    evidence: list[Evidence]  # kinds present on the source's records, in Evidence order
    monthly_median: int | None = None  # integer dollars; lending scope only


class WorkerSummary(Strict):
    """What summarize_worker() returns; attestation.py builds from this by whitelist.

    Only A-C records count. `sources` lists only sources whose tier is A-C.
    """

    period: Period
    sources: list[SourceSummary]
    summary: Summary
    monthly_series: list[MonthAmount] | None = None  # lending scope only


# --- API request and response bodies (BUILD_GUIDE section 8) -----------------------


class TimelineSource(Strict):
    source_id: str
    label: str
    type: SourceType
    tier: Tier
    evidence: list[Evidence]


class TimelineRecord(IncomeRecord):
    """An income record after bank matching, with its tier."""

    tier: Tier


class TimelineMonth(Strict):
    net_cents: int  # A-C records; the same basis as the attestation summary
    self_reported_cents: int = 0  # D records; shown but not counted


class TimelineResponse(Strict):
    """GET /workers/{worker_id}/timeline -> fixtures/timeline.json"""

    worker_id: str
    display_name: str
    language: str
    period: Period
    sources: list[TimelineSource]
    records: list[TimelineRecord]  # sorted by paid_on
    months: dict[str, TimelineMonth]  # "2026-04" -> totals, one key per month in period


class ChecksResponse(Strict):
    """GET /workers/{worker_id}/checks -> fixtures/checks.json"""

    checks: list[Check]


class ExplainRequest(Strict):
    """POST /checks/{check_id}/explain"""

    language: str = "en"


class ExplainResponse(Strict):
    """-> fixtures/explain.json. source says whether the AI or the template wrote it."""

    text: str
    source: Literal["ai", "template"]


class AttestationRequest(Strict):
    """POST /attestations and POST /attestations/preview.

    period defaults to the worker's whole period.
    """

    worker_id: str
    scope: Scope = Scope.rental
    period: Period | None = None


class DisclosureItem(Strict):
    key: str  # stable id, e.g. "monthly_median", "hours"
    label: str  # English text shown to the worker
    reason: Literal["never", "scope"] | None = None  # excluded only: forbidden, or outside this scope


class PreviewResponse(Strict):
    """-> fixtures/preview.json. attestation is unsigned; its attestation_id is "preview"."""

    included: list[DisclosureItem]
    excluded: list[DisclosureItem]
    attestation: Attestation


class IssueResponse(Strict):
    """POST /attestations -> fixtures/attestation.json"""

    attestation: Attestation
    verify_url: str  # f"{PUBLIC_WEB_URL}/v/{attestation_id}"


class VerifyResponse(Strict):
    """GET /attestations/{id}/verify -> fixtures/verify_*.json.

    not_found returns HTTP 404 with only {"status": "not_found"}.
    """

    status: AttestationStatus
    signature_valid: bool | None = None
    attestation: Attestation | None = None
    revoked_at: datetime | None = None


class RevokeResponse(Strict):
    """POST /attestations/{id}/revoke -> fixtures/revoke.json"""

    status: Literal["revoked"] = "revoked"
    attestation_id: str
    revoked_at: datetime


class PublicKey(Strict):
    key_id: str
    alg: Literal["Ed25519"] = "Ed25519"
    public_key: str  # base64 of the raw 32-byte Ed25519 public key


class KeysResponse(Strict):
    """GET /.well-known/baeslip-keys.json -> fixtures/keys.json"""

    keys: list[PublicKey]


class HealthResponse(Strict):
    status: Literal["ok"] = "ok"
