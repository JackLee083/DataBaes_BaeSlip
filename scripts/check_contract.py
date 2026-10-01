#!/usr/bin/env python3
"""Contract check.

    python scripts/check_contract.py                 # check
    python scripts/check_contract.py --write-schema  # regenerate schema/attestation.schema.json

Checks that models.py imports, every fixture parses into its model, the schema file
matches the models, and the fixtures agree with each other (sums, summary, whitelist,
signatures). Exits non-zero on any failure.
"""

from __future__ import annotations

import base64
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))


def check_environment() -> None:
    """Stop early if this is not the pinned environment (CC-2).

    A system Python with other package versions (for example Pydantic 2.8.2 instead of the
    pinned 2.13.5) gives confusing failures later, so compare the interpreter and every pinned
    package in backend/requirements.txt before anything else is imported.
    """
    from importlib import metadata

    problems: list[str] = []
    want_py = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    have_py = f"{sys.version_info.major}.{sys.version_info.minor}"
    if have_py != want_py:
        problems.append(f"Python {have_py} is running; the project needs Python {want_py}")

    pin = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)(?:\[[^\]]*\])?==([^\s;#]+)\s*$")
    for line in (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").splitlines():
        found = pin.match(line.strip())  # lines with platform markers (';') are skipped on purpose
        if not found:
            continue
        name, wanted = found.groups()
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            problems.append(f"{name} is not installed (pinned {wanted})")
            continue
        if installed != wanted:
            problems.append(f"{name} {installed} is installed (pinned {wanted})")

    if problems:
        print("ENVIRONMENT MISMATCH: this is not the pinned environment.", file=sys.stderr)
        for problem in problems[:5]:
            print(f"  - {problem}", file=sys.stderr)
        if len(problems) > 5:
            print(f"  ... and {len(problems) - 5} more", file=sys.stderr)
        print(
            "You are probably not using backend/.venv. Run `bash scripts/setup.sh`, then activate the venv\n"
            "(source backend/.venv/bin/activate) or call backend/.venv/bin/python directly\n"
            "(Windows: backend/.venv/Scripts/python.exe).",
            file=sys.stderr,
        )
        sys.exit(2)


check_environment()

from app import models as m  # noqa: E402

FIXTURES = ROOT / "fixtures"
SCHEMA = ROOT / "schema" / "attestation.schema.json"
MEI = ROOT / "backend" / "app" / "data" / "mei.json"

FIXTURE_MODELS = {
    "timeline.json": m.TimelineResponse,
    "checks.json": m.ChecksResponse,
    "explain.json": m.ExplainResponse,
    "preview.json": m.PreviewResponse,
    "attestation.json": m.IssueResponse,
    "verify_valid.json": m.VerifyResponse,
    "verify_revoked.json": m.VerifyResponse,
    "verify_expired.json": m.VerifyResponse,
    "verify_not_found.json": m.VerifyResponse,
    "revoke.json": m.RevokeResponse,
    "keys.json": m.KeysResponse,
}
BANNED_TITLE_WORDS = ("violat", "stole", "steal", "illegal", "breach")
REQUIRED_TITLE = re.compile(r"\b(may|needs review|unable to verify)\b", re.IGNORECASE)

failures: list[str] = []


def check(ok: bool, msg: str) -> None:
    if not ok:
        failures.append(msg)


def forbidden_keys(obj, path="") -> list[str]:
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in m.FORBIDDEN_ATTESTATION_KEYS:
                found.append(f"{path}.{k}")
            found += forbidden_keys(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += forbidden_keys(v, f"{path}[{i}]")
    return found


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def check_schema(write: bool) -> None:
    expected = m.attestation_schema()
    if write:
        SCHEMA.parent.mkdir(parents=True, exist_ok=True)
        SCHEMA.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {SCHEMA.relative_to(ROOT)}")
    if not SCHEMA.exists():
        check(False, "schema/attestation.schema.json is missing (run with --write-schema)")
        return
    check(json.loads(SCHEMA.read_text()) == expected,
          "schema/attestation.schema.json does not match models.Attestation (run with --write-schema)")


def load_fixtures() -> dict[str, tuple[dict, object]]:
    present = {p.name for p in FIXTURES.glob("*.json")}
    for name in sorted(present - FIXTURE_MODELS.keys()):
        check(False, f"fixtures/{name} has no model in FIXTURE_MODELS")
    loaded = {}
    for name, model in FIXTURE_MODELS.items():
        path = FIXTURES / name
        if not path.exists():
            check(False, f"fixtures/{name} is missing")
            continue
        raw = json.loads(path.read_text())
        try:
            loaded[name] = (raw, model.model_validate(raw))
        except Exception as e:  # noqa: BLE001
            check(False, f"fixtures/{name} does not parse into {model.__name__}: {e}")
    return loaded


def check_attestation(where: str, raw: dict, keys: dict[str, str], signed: bool) -> None:
    att = m.Attestation.model_validate(raw)
    check(att.model_dump(mode="json", exclude_none=True) == raw,
          f"{where}: not in wire form (model_dump(mode='json', exclude_none=True))")
    bad = forbidden_keys(raw)
    check(not bad, f"{where}: forbidden keys {bad}")
    if att.scope == m.Scope.rental:
        check("monthly_series" not in raw, f"{where}: rental attestation has monthly_series")
        check(all("monthly_median" not in s for s in raw["sources"]),
              f"{where}: rental attestation has per-source monthly_median")
    check(att.expires_at - att.issued_at == timedelta(days=30),
          f"{where}: expires_at is not issued_at + 30 days")
    if not signed:
        check(att.signature is None, f"{where}: preview must be unsigned")
        return
    if att.signature is None:
        check(False, f"{where}: missing signature")
        return
    pub = keys.get(att.issuer.key_id)
    if pub is None:
        check(False, f"{where}: key_id {att.issuer.key_id} not in keys.json")
        return
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    body = {k: v for k, v in raw.items() if k != "signature"}
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(pub)).verify(
            base64.b64decode(att.signature.value), canonical(body))
    except InvalidSignature:
        check(False, f"{where}: signature does not verify against keys.json")


def check_consistency(fx: dict[str, tuple[dict, object]]) -> None:
    keys = {k.key_id: k.public_key for k in fx["keys.json"][1].keys} if "keys.json" in fx else {}

    # timeline: month totals equal record sums; one key per month in period
    if "timeline.json" in fx:
        tl: m.TimelineResponse = fx["timeline.json"][1]
        sums: dict[str, dict[str, int]] = defaultdict(lambda: {"net": 0, "d": 0})
        for r in tl.records:
            sums[r.paid_on.strftime("%Y-%m")]["d" if r.tier == m.Tier.D else "net"] += r.net_cents
        for month, tot in tl.months.items():
            check(tot.net_cents == sums[month]["net"] and tot.self_reported_cents == sums[month]["d"],
                  f"timeline.json: months[{month}] does not equal its records")
        check(set(sums) <= set(tl.months), "timeline.json: records outside months")
        check([r.paid_on for r in tl.records] == sorted(r.paid_on for r in tl.records),
              "timeline.json: records not sorted by paid_on")
        tiers = {s.source_id: s.tier for s in tl.sources}
        for r in tl.records:
            if r.source_id not in tiers:
                check(False, f"timeline.json: {r.record_id} has unknown source {r.source_id}")
            else:  # a source's tier is its weakest record's tier ("A" < "D")
                check(r.tier.value <= tiers[r.source_id].value,
                      f"timeline.json: {r.record_id} is weaker than its source tier")

        # attestation summary equals the timeline, and sources are the A-C timeline sources
        dollars = [round(v.net_cents / 100) for v in tl.months.values() if v.net_cents]
        want_summary = {
            "currency": "AUD",
            "monthly_income_range": {"low": min(dollars), "high": max(dollars)},
            "monthly_median": round(statistics.median(dollars)),
            "coverage": {"months_with_data": len(dollars), "months_in_period": len(tl.months)},
        }
        want_sources = [
            {"label": s.label, "type": s.type.value, "tier": s.tier.value, "evidence": [e.value for e in s.evidence]}
            for s in tl.sources if s.tier != m.Tier.D
        ]
        for name in ("attestation.json", "preview.json", "verify_valid.json"):
            if name in fx:
                a = fx[name][0]["attestation"]
                check(a["summary"] == want_summary, f"{name}: summary {a['summary']} != timeline {want_summary}")
                check(a["sources"] == want_sources, f"{name}: sources differ from A-C timeline sources")

    for name in ("attestation.json", "verify_valid.json", "verify_revoked.json", "verify_expired.json"):
        if name in fx:
            check_attestation(name, fx[name][0]["attestation"], keys, signed=True)
    if "preview.json" in fx:
        check_attestation("preview.json", fx["preview.json"][0]["attestation"], keys, signed=False)
        excluded = {i.key for i in fx["preview.json"][1].excluded}
        check({"hours", "visa", "transactions", "checks"} <= excluded,
              "preview.json: excluded must list hours, visa, transactions and checks")

    same = [fx[n][0]["attestation"] for n in ("attestation.json", "verify_valid.json", "verify_revoked.json") if n in fx]
    check(all(a == same[0] for a in same), "attestation.json, verify_valid.json and verify_revoked.json differ")
    if "attestation.json" in fx:
        issue = fx["attestation.json"][1]
        check(issue.verify_url.endswith(f"/v/{issue.attestation.attestation_id}"),
              "attestation.json: verify_url must end with /v/<attestation_id>")
    for name, status in (("verify_valid.json", "valid"), ("verify_revoked.json", "revoked"),
                         ("verify_expired.json", "expired"), ("verify_not_found.json", "not_found")):
        if name in fx:
            check(fx[name][0]["status"] == status, f"{name}: status must be {status}")
    if "verify_not_found.json" in fx:
        check(fx["verify_not_found.json"][0] == {"status": "not_found"},
              "verify_not_found.json must be exactly {\"status\": \"not_found\"}")
    if "revoke.json" in fx and "attestation.json" in fx:
        check(fx["revoke.json"][1].attestation_id == fx["attestation.json"][1].attestation.attestation_id,
              "revoke.json: attestation_id differs from attestation.json")

    if "checks.json" in fx:
        for c in fx["checks.json"][1].checks:
            if None not in (c.expected_cents, c.actual_cents, c.difference_cents):
                check(c.difference_cents == c.expected_cents - c.actual_cents,
                      f"checks.json: {c.check_id} difference != expected - actual")
            check(not any(w in c.title.lower() for w in BANNED_TITLE_WORDS),
                  f"checks.json: {c.check_id} title uses banned wording")
            check(bool(REQUIRED_TITLE.search(c.title)),
                  f"checks.json: {c.check_id} title must say 'may', 'needs review' or 'unable to verify'")
            check(c.check_id.startswith(c.rule.lower() + "-"), f"checks.json: {c.check_id} id/rule mismatch")


def check_mock_data() -> None:
    if not MEI.exists():
        print("note: backend/app/data/mei.json not written yet; skipped")
        return
    try:
        m.Worker.model_validate_json(MEI.read_text())
    except Exception as e:  # noqa: BLE001
        check(False, f"backend/app/data/mei.json does not parse into Worker: {e}")


def main() -> int:
    check_schema(write="--write-schema" in sys.argv)
    fx = load_fixtures()
    check_consistency(fx)
    check_mock_data()
    if failures:
        print("CONTRACT CHECK FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"contract check passed: models import, {len(fx)} fixtures parse and agree, schema matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
