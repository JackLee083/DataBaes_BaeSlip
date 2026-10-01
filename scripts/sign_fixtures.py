#!/usr/bin/env python3
"""Re-sign the fixtures with a fresh Ed25519 key that lives only in memory.

    backend/.venv/bin/python scripts/sign_fixtures.py

Sets the issuer fields from app.config.Config, signs attestation.json and the three
verify_*.json fixtures with app.signing.sign, and publishes the new public key in keys.json.
The private key is never written, printed or logged, so the fixtures cannot be re-signed
with the same key later; each run replaces the public key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from app.config import Config  # noqa: E402
from app.signing import public_key_b64, sign  # noqa: E402

SIGNED = ("attestation.json", "verify_valid.json", "verify_revoked.json", "verify_expired.json")
UNSIGNED = ("preview.json",)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resign(fixtures_dir: Path, issuer_id: str, issuer_name: str, key_id: str) -> None:
    fixtures_dir = Path(fixtures_dir)
    key = Ed25519PrivateKey.generate()  # memory only

    for name in (*SIGNED, *UNSIGNED):
        path = fixtures_dir / name
        data = _read(path)
        att = data["attestation"]
        att["issuer"]["issuer_id"] = issuer_id
        att["issuer"]["name"] = issuer_name
        if name in SIGNED:
            att = sign(att, key)
        data["attestation"] = att
        _write(path, data)
        print(f"wrote {name}")

    keys_path = fixtures_dir / "keys.json"
    keys = _read(keys_path)
    entry = next(k for k in keys["keys"] if k["key_id"] == key_id)
    entry["public_key"] = public_key_b64(key)
    _write(keys_path, keys)
    print(f"wrote keys.json (key_id {key_id}, public key {entry['public_key']})")


def main() -> int:
    cfg = Config()
    resign(ROOT / "fixtures", cfg.issuer_id, cfg.issuer_name, cfg.key_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
