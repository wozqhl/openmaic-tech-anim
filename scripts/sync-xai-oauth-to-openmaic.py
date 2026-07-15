#!/usr/bin/env python3
"""Sync a working Hermes xAI OAuth access_token into OpenMAIC .env.local.

Why: API keys may hit monthly spend limit while Hermes OAuth still works.
Run when OpenMAIC verify-model returns 401/403/Forbidden.

Usage:
  python3 scripts/sync-xai-oauth-to-openmaic.py
  python3 scripts/sync-xai-oauth-to-openmaic.py --restart
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
AUTH = HOME / ".hermes" / "auth.json"
OPENMAIC_ENV = HOME / "OpenMAIC" / ".env.local"
PROXY = "http://127.0.0.1:7890"


def find_working_token() -> str:
    if not AUTH.exists():
        raise SystemExit(f"missing {AUTH}")
    data = json.loads(AUTH.read_text())
    pool = (data.get("credential_pool") or {}).get("xai-oauth") or []
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    for item in pool:
        tok = item.get("access_token") or ""
        if not tok:
            continue
        req = urllib.request.Request(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {tok}"},
        )
        try:
            with opener.open(req, timeout=20) as r:
                if r.status == 200:
                    print(f"OK token id={item.get('id')} len={len(tok)}")
                    return tok
        except Exception as e:
            print(f"skip {item.get('id')}: {type(e).__name__}")
    raise SystemExit("no working xai-oauth access_token in Hermes auth.json")


def set_env_var(text: str, key: str, value: str) -> str:
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f"{key}={value}"
    if pat.search(text):
        return pat.sub(line, text)
    return text.rstrip() + "\n" + line + "\n"


def write_openmaic_env(token: str) -> None:
    if not OPENMAIC_ENV.exists():
        raise SystemExit(f"missing {OPENMAIC_ENV}")
    text = OPENMAIC_ENV.read_text()
    for key in ("GROK_API_KEY", "TTS_OPENAI_API_KEY", "IMAGE_GROK_API_KEY"):
        text = set_env_var(text, key, token)
    for k, v in {
        "HTTP_PROXY": PROXY,
        "HTTPS_PROXY": PROXY,
        "http_proxy": PROXY,
        "https_proxy": PROXY,
        "NODE_USE_ENV_PROXY": "1",
        "DEFAULT_MODEL": "grok:grok-4.5",
    }.items():
        text = set_env_var(text, k, v)
    OPENMAIC_ENV.write_text(text)
    OPENMAIC_ENV.chmod(0o600)
    print(f"updated {OPENMAIC_ENV}")


def restart_openmaic() -> None:
    subprocess.run(
        "lsof -tiTCP:3000 -sTCP:LISTEN | xargs kill -9 2>/dev/null",
        shell=True,
    )
    time.sleep(1)
    root = HOME / "OpenMAIC"
    env = os.environ.copy()
    for line in OPENMAIC_ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    log = Path("/tmp/openmaic-oauth-restart.log")
    f = open(log, "ab", buffering=0)
    subprocess.Popen(
        ["pnpm", "dev"],
        cwd=str(root),
        env=env,
        stdout=f,
        stderr=f,
        start_new_session=True,
    )
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:3000/api/health", timeout=2) as r:
                if r.status == 200:
                    print("OpenMAIC health OK")
                    break
        except Exception:
            time.sleep(0.5)
    else:
        print("OpenMAIC health timeout; see", log)
        return
    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/verify-model",
        data=json.dumps({"model": "grok:grok-4.5"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            print("verify-model:", r.read().decode()[:200])
    except Exception as e:
        print("verify-model failed:", e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restart", action="store_true", help="Restart OpenMAIC pnpm dev after sync")
    args = ap.parse_args()
    tok = find_working_token()
    write_openmaic_env(tok)
    if args.restart:
        restart_openmaic()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
