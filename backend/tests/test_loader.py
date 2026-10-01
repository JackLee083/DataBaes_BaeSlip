import json
from pathlib import Path

import pytest

from app.interfaces import WorkerNotFound
from app.services import loader

MINIMAL = {
    "worker_id": "tester",
    "display_name": "Test T.",
    "language": "zh-Hant",
    "visa": None,
    "today": "2026-09-29",
    "period_start": "2026-07-01",
    "period_end": "2026-09-29",
    "sources": [],
    "income": [],
    "shifts": [],
    "platform_days": [],
    "platform_payouts": [],
    "super_contributions": [],
    "bank_deposits": [],
}


def _write(dir_: Path, worker_id: str = "tester", data: dict | None = None) -> None:
    (dir_ / f"{worker_id}.json").write_text(json.dumps(data or MINIMAL), encoding="utf-8")


def test_loads_minimal_worker_from_tmp_dir(tmp_path):
    _write(tmp_path)
    w = loader.load_worker("tester", data_dir=tmp_path)
    assert w.worker_id == "tester"
    assert w.display_name == "Test T."
    assert w.sources == []


def test_unknown_worker_raises(tmp_path):
    with pytest.raises(WorkerNotFound):
        loader.load_worker("nobody", data_dir=tmp_path)


def test_returns_independent_copies(tmp_path):
    _write(tmp_path)
    a = loader.load_worker("tester", data_dir=tmp_path)
    a.display_name = "Mutated"
    a.sources.append("junk")  # type: ignore[arg-type]
    b = loader.load_worker("tester", data_dir=tmp_path)
    assert b is not a
    assert b.display_name == "Test T."
    assert b.sources == []


@pytest.mark.parametrize("bad", ["../x", "a/b", "A", "", "a.b", "..", "x\n", "a b"])
def test_rejects_path_like_ids(tmp_path, bad):
    _write(tmp_path)
    (tmp_path.parent / "x.json").write_text(json.dumps(MINIMAL), encoding="utf-8")
    with pytest.raises(WorkerNotFound):
        loader.load_worker(bad, data_dir=tmp_path)


def test_interfaces_and_loader_import_together(tmp_path, monkeypatch):
    from app import interfaces

    _write(tmp_path)
    monkeypatch.setattr(loader, "DATA_DIR", tmp_path)
    real = loader.load_worker
    monkeypatch.setattr(loader, "load_worker", lambda wid: real(wid, data_dir=tmp_path))
    assert interfaces.load_worker("tester").worker_id == "tester"
    with pytest.raises(interfaces.WorkerNotFound):
        interfaces.load_worker("nobody")
