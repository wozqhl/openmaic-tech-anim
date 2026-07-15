#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Isolate from Hermes/global venv pollution
export PATH="$ROOT/.venv/bin:/usr/bin:/bin:/opt/homebrew/bin:${PATH:-}"
export PYTHONPATH="$ROOT"
unset VIRTUAL_ENV || true
# strip accidental hermes site-packages from PYTHONPATH-like pollution
export OPENMAIC_BASE_URL="${OPENMAIC_BASE_URL:-http://127.0.0.1:3000}"
export OPENMAIC_MODEL="${OPENMAIC_MODEL:-grok:grok-4.5}"

PORT="${PORT:-8765}"
echo "TechAnim Web → http://127.0.0.1:${PORT}"
exec "$ROOT/.venv/bin/python" -m uvicorn web.app:app --host 0.0.0.0 --port "$PORT"
