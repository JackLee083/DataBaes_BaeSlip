"""Issued attestations in a JSON file: {att_id: {"attestation": {...}, "revoked_at": null}}."""

import json
import os
import secrets
import tempfile
from datetime import datetime
from pathlib import Path

from app.models import AttestationStatus


def new_attestation_id() -> str:
    """"att_" + secrets.token_urlsafe(8): unguessable."""
    return "att_" + secrets.token_urlsafe(8)


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _read(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def save(self, attestation: dict) -> None:
        data = self._read()
        data[attestation["attestation_id"]] = {"attestation": attestation, "revoked_at": None}
        self._write(data)

    def get(self, att_id: str) -> dict | None:
        return self._read().get(att_id)

    def revoke(self, att_id: str, now: datetime) -> dict | None:
        data = self._read()
        entry = data.get(att_id)
        if entry is None:
            return None
        if entry.get("revoked_at") is None:
            entry["revoked_at"] = now.isoformat()
            self._write(data)
        return entry


def status_of(entry: dict | None, now: datetime) -> AttestationStatus:
    if entry is None:
        return AttestationStatus.not_found
    if entry.get("revoked_at"):
        return AttestationStatus.revoked
    if now > datetime.fromisoformat(entry["attestation"]["expires_at"]):
        return AttestationStatus.expired
    return AttestationStatus.valid
