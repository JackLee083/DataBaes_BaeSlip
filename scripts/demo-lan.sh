#!/usr/bin/env bash
# Phone demo on the local network. Finds this machine's current LAN IP, writes it into
# backend/.env (PUBLIC_WEB_URL) and frontend/.env.local (VITE_API_BASE), then starts both
# servers listening on the network. Rerun it whenever the IP changes (new Wi-Fi or hotspot).
#   bash scripts/demo-lan.sh             # backend + frontend (live API)
#   bash scripts/demo-lan.sh fixtures    # frontend only, from the committed fixtures
#   DEMO_IP=192.168.1.20 bash scripts/demo-lan.sh   # use this IP instead of detecting one
# Ctrl+C stops both servers.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-live}"
fail() { echo "DEMO FAILED: $*" >&2; exit 1; }

detect_ip() {
  local ip=""
  if command -v ipconfig >/dev/null 2>&1; then  # macOS: Wi-Fi is usually en0
    for iface in en0 en1 en2; do
      ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
      [ -n "$ip" ] && break
    done
  fi
  if [ -z "$ip" ] && command -v hostname >/dev/null 2>&1; then  # Linux
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  echo "$ip"
}

# Sets KEY=VALUE in an env file, keeping every other line (API keys stay untouched).
set_env() {
  local file="$1" key="$2" value="$3" tmp
  touch "$file"
  tmp="$(mktemp)"
  grep -v "^${key}=" "$file" > "$tmp" || true
  [ -s "$tmp" ] && [ -n "$(tail -c1 "$tmp")" ] && echo >> "$tmp"
  echo "${key}=${value}" >> "$tmp"
  mv "$tmp" "$file"
}

port_free() { ! (command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1); }

case "$MODE" in live|fixtures) ;; *) fail "unknown mode '$MODE' (use live or fixtures)";; esac

IP="${DEMO_IP:-$(detect_ip)}"
[ -n "$IP" ] || fail "no LAN IP found. Connect to Wi-Fi or a hotspot, or set DEMO_IP."
[ -d "$ROOT/frontend/node_modules" ] || fail "frontend not installed. Run: bash scripts/setup.sh"
port_free 5173 || fail "port 5173 is busy. Stop the other dev server first."

WEB="http://${IP}:5173"
API="http://${IP}:8000"
BACKEND_PID=""
cleanup() { [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

if [ "$MODE" = live ]; then
  [ -x "$ROOT/backend/.venv/bin/uvicorn" ] || fail "backend not installed. Run: bash scripts/setup.sh"
  port_free 8000 || fail "port 8000 is busy. Stop the other backend first."
  set_env "$ROOT/backend/.env" PUBLIC_WEB_URL "$WEB"
  set_env "$ROOT/frontend/.env.local" VITE_USE_FIXTURES false
  set_env "$ROOT/frontend/.env.local" VITE_API_BASE "$API"
  (cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env) &
  BACKEND_PID=$!
  for _ in $(seq 1 20); do
    curl -fs "$API/health" >/dev/null 2>&1 && break
    kill -0 "$BACKEND_PID" 2>/dev/null || fail "backend did not start (see the error above)"
    sleep 0.5
  done
  curl -fs "$API/health" >/dev/null 2>&1 || fail "backend did not answer on $API/health"
  export VITE_USE_FIXTURES=false VITE_API_BASE="$API"
else
  # Shell variables win over .env.local, so fixture mode needs no file change.
  export VITE_USE_FIXTURES=true
fi

cat <<EOF

== BaeSlip phone demo ($MODE)
   On this computer, open:  $WEB/app
   The phone must be on the same network. The QR code will point at $WEB/v/...
   IP changed? Stop with Ctrl+C and run this script again.

EOF
cd "$ROOT/frontend"
npm run dev -- --host --strictPort
