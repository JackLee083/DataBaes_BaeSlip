#!/usr/bin/env bash
# One-command environment setup. Everyone (humans and agents) runs this; it installs the exact
# pinned versions and verifies them. Windows: run it in Git Bash or WSL.
#   bash scripts/setup.sh           # backend + frontend
#   bash scripts/setup.sh backend   # backend only
#   bash scripts/setup.sh frontend  # frontend only
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PART="${1:-all}"
fail() { echo "SETUP FAILED: $*" >&2; exit 1; }

setup_backend() {
  echo "== backend: Python $(cat "$ROOT/.python-version") from backend/requirements.txt"
  cd "$ROOT/backend"
  if command -v uv >/dev/null 2>&1; then
    uv venv --quiet --allow-existing --python "$(cat "$ROOT/.python-version")" .venv
    uv pip install --quiet --python .venv -r requirements.txt
  else
    PY=""
    for c in python3.11 python3 python; do
      if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 11))'; then PY="$c"; break; fi
    done
    [ -n "$PY" ] || fail "Python 3.11 not found. Install uv (https://docs.astral.sh/uv/) or Python 3.11, then rerun."
    "$PY" -m venv .venv
    if [ -x .venv/bin/python ]; then VPY=.venv/bin/python; else VPY=.venv/Scripts/python.exe; fi
    "$VPY" -m pip install --quiet --upgrade pip
    "$VPY" -m pip install --quiet -r requirements.txt
  fi
  if [ -x .venv/bin/python ]; then VPY=.venv/bin/python; else VPY=.venv/Scripts/python.exe; fi
  "$VPY" -c 'import sys; assert sys.version_info[:2] == (3, 11), sys.version' || fail "venv is not Python 3.11"
  (cd "$ROOT" && "backend/$VPY" scripts/check_contract.py)
  "$VPY" -m pytest -q
  echo "== backend OK. Activate with: source backend/.venv/bin/activate"
}

setup_frontend() {
  echo "== frontend: Node $(cat "$ROOT/frontend/.nvmrc") with npm ci"
  command -v node >/dev/null 2>&1 || fail "Node not found. Install Node 22 (e.g. nvm install 22)."
  node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=12)?0:1)' \
    || fail "Node $(node --version) is too old. Need >=22.12 (e.g. nvm install 22 && nvm use 22)."
  cd "$ROOT/frontend"
  npm ci --no-audit --no-fund
  npm run build
  npm test
  echo "== frontend OK"
}

case "$PART" in
  backend) setup_backend ;;
  frontend) setup_frontend ;;
  all) setup_backend; setup_frontend ;;
  *) fail "unknown part: $PART (use backend, frontend or all)" ;;
esac
echo "== setup complete"
