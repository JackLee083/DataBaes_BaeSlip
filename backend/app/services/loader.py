"""Load mock worker data. Owner: data (B1)."""

import re
from pathlib import Path

from app.interfaces import WorkerNotFound
from app.models import Worker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_ID_RE = re.compile(r"[a-z0-9-]+")

# (resolved path, mtime_ns, size) -> parsed Worker. Never handed out directly.
_CACHE: dict[tuple[str, int, int], Worker] = {}


def load_worker(worker_id: str, data_dir: Path = DATA_DIR) -> Worker:
    """Read <data_dir>/<worker_id>.json. Raises interfaces.WorkerNotFound if missing."""
    if not isinstance(worker_id, str) or not _ID_RE.fullmatch(worker_id):
        raise WorkerNotFound(worker_id)
    path = (Path(data_dir) / f"{worker_id}.json").resolve()
    try:
        st = path.stat()
    except OSError:
        raise WorkerNotFound(worker_id) from None
    key = (str(path), st.st_mtime_ns, st.st_size)
    worker = _CACHE.get(key)
    if worker is None:
        worker = Worker.model_validate_json(path.read_bytes())
        for stale in [k for k in _CACHE if k[0] == key[0]]:
            del _CACHE[stale]
        _CACHE[key] = worker
    return worker.model_copy(deep=True)
