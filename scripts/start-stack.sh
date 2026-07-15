#!/usr/bin/env bash
# Start TechAnim stack: OpenMAIC proxies (if present) + OpenMAIC dev + TechAnim Web
set -euo pipefail
OPENMAIC="${OPENMAIC_HOME:-$HOME/OpenMAIC}"
TECHANIM="${TECHANIM_HOME:-$HOME/openmaic-tech-anim}"

echo "== TechAnim stack =="

# Clash hint
if ! curl -sS -m 2 -x http://127.0.0.1:7890 -o /dev/null -w '' https://api.x.ai/v1/models 2>/dev/null; then
  echo "WARN: Clash :7890 may be down — OpenMAIC/xAI may fail without proxy"
fi

# OpenMAIC proxies
if [[ -x "$OPENMAIC/scripts/start-proxies.sh" ]]; then
  bash "$OPENMAIC/scripts/start-proxies.sh" || true
elif [[ -f "$OPENMAIC/scripts/ddgs-tavily-proxy.py" ]]; then
  if ! curl -fsS -m 1 http://127.0.0.1:8787/health >/dev/null 2>&1; then
    (
      export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890
      export HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890
      nohup "$OPENMAIC/.venv-proxies/bin/python" "$OPENMAIC/scripts/ddgs-tavily-proxy.py" \
        >/tmp/ddgs-proxy.log 2>&1 &
    )
  fi
fi

# OpenMAIC :3000
if ! curl -fsS -m 2 http://127.0.0.1:3000/api/health >/dev/null 2>&1; then
  echo "Starting OpenMAIC..."
  # sync oauth if available
  if [[ -f "$TECHANIM/scripts/sync-xai-oauth-to-openmaic.py" ]]; then
    python3 "$TECHANIM/scripts/sync-xai-oauth-to-openmaic.py" || true
  fi
  (
    set -a
    # shellcheck disable=SC1091
    [[ -f "$OPENMAIC/.env.local" ]] && source "$OPENMAIC/.env.local" || true
    set +a
    export HTTP_PROXY="${HTTP_PROXY:-http://127.0.0.1:7890}"
    export HTTPS_PROXY="${HTTPS_PROXY:-http://127.0.0.1:7890}"
    export NODE_USE_ENV_PROXY=1
    cd "$OPENMAIC"
    nohup pnpm dev >/tmp/openmaic-dev.log 2>&1 &
  )
  for i in $(seq 1 40); do
    curl -fsS -m 2 http://127.0.0.1:3000/api/health >/dev/null 2>&1 && break
    sleep 0.5
  done
fi
echo "OpenMAIC: $(curl -fsS -m 2 http://127.0.0.1:3000/api/health || echo DOWN)"

# TechAnim web :8765
if ! curl -fsS -m 2 http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
  echo "Starting TechAnim Web..."
  bash "$TECHANIM/scripts/start-web.sh" >/tmp/techanim-web.log 2>&1 &
  for i in $(seq 1 30); do
    curl -fsS -m 2 http://127.0.0.1:8765/api/health >/dev/null 2>&1 && break
    sleep 0.3
  done
fi
echo "TechAnim: $(curl -fsS -m 2 http://127.0.0.1:8765/api/health || echo DOWN)"
echo "UI → http://localhost:8765"
echo "OpenMAIC → http://localhost:3000"
