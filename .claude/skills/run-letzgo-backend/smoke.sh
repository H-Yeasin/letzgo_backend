#!/bin/bash
# LetzGo Backend — smoke test: launch, verify, stop
#
# Usage:
#   bash smoke.sh            # full smoke test (launch → test → stop)
#   bash smoke.sh --launch   # start server in background only
#   bash smoke.sh --test     # run smoke tests against a running server
#   bash smoke.sh --stop     # stop the background server
#
# Default port: 8000 — override with PORT=4000 ./smoke.sh

# Not using set -e — curl pipes + grep can exit non-zero on expected conditions

PORT="${PORT:-8000}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PID_FILE="/tmp/letzgo-backend.pid"
LOG_FILE="/tmp/letzgo-backend.log"

launch() {
  cd "$ROOT"
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "→ Backend already running (PID $(cat "$PID_FILE"))"
    return 0
  fi

  # Verify critical packages are installed; install if missing
  if ! python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "→ Installing Python dependencies…"
    pip install -r requirements.txt 2>&1 | tail -5
  else
    echo "→ Python dependencies already installed"
  fi

  echo "→ Starting backend on port $PORT…"
  nohup python -m scripts.run > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"

  # Wait for startup
  for i in $(seq 1 30); do
    curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1 && break
    sleep 1
  done

  if curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "✓ Backend is up (PID $(cat "$PID_FILE"))"
  else
    echo "✗ Backend failed to start — check $LOG_FILE"
    return 1
  fi
}

test_smoke() {
  local base="http://localhost:$PORT"
  local failed=0

  echo "→ Running smoke tests…"

  # Health check
  if curl -sf "$base/health" | grep -q '"healthy"'; then
    echo "  ✓ /health returns healthy"
  else
    echo "  ✗ /health failed"
    failed=1
  fi

  # Root endpoint
  if curl -sf "$base/" | grep -q '"running"'; then
    echo "  ✓ / returns running status"
  else
    echo "  ✗ / failed"
    failed=1
  fi

  # API docs (DEBUG mode)
  if curl -s "$base/docs" | grep -qi "swagger"; then
    echo "  ✓ /docs serves Swagger UI"
  else
    echo "  ✗ /docs failed"
    failed=1
  fi

  # OpenAPI schema
  if curl -s "$base/openapi.json" | grep -q "openapi"; then
    echo "  ✓ /openapi.json serves schema"
  else
    echo "  ✗ /openapi.json failed"
    failed=1
  fi

  if [ "$failed" -eq 0 ]; then
    echo "✓ All smoke tests passed"
  else
    echo "✗ Some smoke tests failed"
  fi
  return "$failed"
}

stop_server() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "→ Stopping backend (PID $pid)…"
      kill "$pid" 2>/dev/null || true
      sleep 1
      echo "✓ Backend stopped"
    fi
    rm -f "$PID_FILE"
  fi
  # Kill any lingering uvicorn/python processes
  taskkill //F //IM python.exe 2>/dev/null || true
  pkill -f "python.*scripts.run" 2>/dev/null || true
}

# ── Main ──────────────────────────────────────────────────────────────
case "${1:-all}" in
  --launch) launch ;;
  --test)   test_smoke ;;
  --stop)   stop_server ;;
  all)
    launch
    test_smoke
    stop_server
    ;;
  *)
    echo "Usage: $0 [--launch | --test | --stop | all]"
    exit 1
    ;;
esac
