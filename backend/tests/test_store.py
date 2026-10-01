from datetime import datetime, timedelta, timezone

from app.models import AttestationStatus
from app.services.store import Store, new_attestation_id, status_of

EXPIRES = "2026-10-29T10:00:00+10:00"
EXP_DT = datetime.fromisoformat(EXPIRES)


def make_att(att_id="att_test1234"):
    return {
        "attestation_id": att_id,
        "issued_at": "2026-09-29T10:00:00+10:00",
        "expires_at": EXPIRES,
        "signature": "sig",
    }


def test_status_of():
    att = make_att()
    before = EXP_DT - timedelta(days=1)
    after = EXP_DT + timedelta(seconds=1)
    entry = {"attestation": att, "revoked_at": None}
    assert status_of(entry, before) == AttestationStatus.valid
    assert status_of(entry, after) == AttestationStatus.expired
    revoked = {"attestation": att, "revoked_at": before.isoformat()}
    assert status_of(revoked, before) == AttestationStatus.revoked
    assert status_of(None, before) == AttestationStatus.not_found


def test_save_get_roundtrip(tmp_path):
    s = Store(tmp_path / "sub" / "store.json")
    assert s.get("att_test1234") is None
    att = make_att()
    s.save(att)
    entry = s.get("att_test1234")
    assert entry == {"attestation": att, "revoked_at": None}


def test_revoke_sets_revoked_at_and_is_idempotent(tmp_path):
    s = Store(tmp_path / "store.json")
    s.save(make_att())
    t1 = datetime(2026, 9, 30, tzinfo=timezone.utc)
    t2 = t1 + timedelta(days=1)
    e1 = s.revoke("att_test1234", t1)
    assert e1["revoked_at"] == t1.isoformat()
    e2 = s.revoke("att_test1234", t2)
    assert e2["revoked_at"] == t1.isoformat()
    assert s.get("att_test1234")["revoked_at"] == t1.isoformat()


def test_revoke_unknown_returns_none(tmp_path):
    assert Store(tmp_path / "store.json").revoke("att_nope", datetime.now(timezone.utc)) is None


def test_persists_across_instances(tmp_path):
    p = tmp_path / "store.json"
    a, b = Store(p), Store(p)
    a.save(make_att())
    assert b.get("att_test1234")["attestation"] == make_att()
    b.revoke("att_test1234", datetime(2026, 9, 30, tzinfo=timezone.utc))
    assert a.get("att_test1234")["revoked_at"] is not None


def test_ids_unique_and_prefixed():
    ids = {new_attestation_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(i.startswith("att_") and len(i) > 8 for i in ids)


def test_boundary():
    entry = {"attestation": make_att(), "revoked_at": None}
    assert status_of(entry, EXP_DT) == AttestationStatus.valid
