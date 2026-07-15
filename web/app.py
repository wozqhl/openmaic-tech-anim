#!/usr/bin/env python3
"""TechAnim Web UI — submit tech topics, run gen/compose, download results.

Run:
  cd ~/openmaic-tech-anim && .venv/bin/uvicorn web.app:app --host 0.0.0.0 --port 8765
Open:
  http://localhost:8765
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)

# In-memory job store (sufficient for local single-user)
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

app = FastAPI(title="TechAnim", version="0.4.0")


class CreateJob(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    audience: str = "工程师与技术爱好者"
    compose: bool = True
    max_scenes: int = Field(0, ge=0, le=20, description="0=all scenes when composing")
    language: str = "zh-CN"


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s.strip())
    return s.strip("-")[:48] or "topic"


def _update(job_id: str, **kw: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kw)
            JOBS[job_id]["updated_at"] = time.time()


def _run_job(job_id: str, body: CreateJob) -> None:
    _update(job_id, status="running", step="gen", message="生成大纲 / Manim / 仿真…")
    env = os.environ.copy()
    # ensure project env; strip SOCKS that breaks httpx
    for k in ("ALL_PROXY", "all_proxy", "SOCKS_PROXY", "socks_proxy"):
        env.pop(k, None)
    env["HTTP_PROXY"] = env["HTTPS_PROXY"] = env["http_proxy"] = env["https_proxy"] = ""
    env.setdefault("OPENMAIC_BASE_URL", "http://127.0.0.1:3000")
    env.setdefault("OPENMAIC_MODEL", "grok:grok-4.5")
    env["PYTHONPATH"] = str(ROOT)
    env["PATH"] = str(ROOT / ".venv/bin") + ":" + env.get("PATH", "")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT / f"{stamp}_{_slug(body.topic)}_web"
    try:
        cmd = [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pipelines.cli",
            "gen",
            body.topic,
            "--audience",
            body.audience,
            "--language",
            body.language,
            "--output",
            str(out_dir),
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            _update(
                job_id,
                status="failed",
                step="gen",
                message="gen failed",
                log=(proc.stdout or "")[-2000:] + "\n" + (proc.stderr or "")[-2000:],
                job_dir=str(out_dir) if out_dir.exists() else None,
            )
            return

        _update(job_id, job_dir=str(out_dir), step="gen_done", message="大纲已生成")

        if body.compose:
            _update(job_id, step="compose", message="豆包 TTS + 合成视频…")
            ccmd = [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "pipelines.cli",
                "compose",
                str(out_dir),
            ]
            if body.max_scenes and body.max_scenes > 0:
                ccmd.extend(["--max-scenes", str(body.max_scenes)])
            cproc = subprocess.run(
                ccmd,
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
            )
            if cproc.returncode != 0:
                _update(
                    job_id,
                    status="failed",
                    step="compose",
                    message="compose failed",
                    log=(cproc.stdout or "")[-2000:] + "\n" + (cproc.stderr or "")[-2000:],
                )
                return
            final = out_dir / "video" / "final.mp4"
            _update(
                job_id,
                status="done",
                step="done",
                message="完成",
                final_video=str(final) if final.exists() else None,
                log=(proc.stdout or "")[-1500:] + "\n" + (cproc.stdout or "")[-1500:],
            )
        else:
            _update(
                job_id,
                status="done",
                step="done",
                message="gen 完成（未合成视频）",
                log=(proc.stdout or "")[-2000:],
            )
    except subprocess.TimeoutExpired:
        _update(job_id, status="failed", step="timeout", message="任务超时")
    except Exception as e:
        _update(job_id, status="failed", step="error", message=str(e))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/health")
def health() -> dict[str, Any]:
    openmaic_ok = False
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:3000/api/health", timeout=3) as r:
            openmaic_ok = r.status == 200
    except Exception:
        openmaic_ok = False
    return {
        "ok": True,
        "service": "techanim-web",
        "openmaic": openmaic_ok,
        "jobs": len(JOBS),
    }


@app.post("/api/jobs")
def create_job(body: CreateJob) -> dict[str, Any]:
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(400, "topic required")
    # WeChat-style shortcut: 「科普一下 XXX」
    m = re.match(r"^(?:科普一下|科普|讲讲|动画讲解)\s*(.+)$", topic)
    if m:
        topic = m.group(1).strip()
        body = body.model_copy(update={"topic": topic})

    job_id = uuid.uuid4().hex[:10]
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "topic": topic,
            "status": "queued",
            "step": "queued",
            "message": "排队中",
            "created_at": time.time(),
            "updated_at": time.time(),
            "compose": body.compose,
            "max_scenes": body.max_scenes,
            "job_dir": None,
            "final_video": None,
            "log": "",
        }
    t = threading.Thread(target=_run_job, args=(job_id, body), daemon=True)
    t.start()
    return {"id": job_id, "status": "queued", "topic": topic}


@app.get("/api/jobs")
def list_jobs() -> dict[str, Any]:
    with JOBS_LOCK:
        items = sorted(JOBS.values(), key=lambda j: j.get("created_at", 0), reverse=True)
    return {"jobs": items[:50]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.get("/api/jobs/{job_id}/files")
def list_files(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or not job.get("job_dir"):
        raise HTTPException(404, "job or artifacts not found")
    root = Path(job["job_dir"])
    if not root.exists():
        raise HTTPException(404, "job dir missing")
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.stat().st_size < 200_000_000:
            rel = str(p.relative_to(root))
            files.append({"path": rel, "size": p.stat().st_size})
    return {"job_dir": str(root), "files": files}


@app.get("/api/jobs/{job_id}/file")
def get_file(job_id: str, path: str) -> FileResponse:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job or not job.get("job_dir"):
        raise HTTPException(404, "job not found")
    root = Path(job["job_dir"]).resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(target)


@app.get("/api/jobs/{job_id}/video")
def get_video(job_id: str) -> FileResponse:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    vid = job.get("final_video")
    if not vid or not Path(vid).is_file():
        # fallback path
        if job.get("job_dir"):
            cand = Path(job["job_dir"]) / "video" / "final.mp4"
            if cand.is_file():
                vid = str(cand)
    if not vid or not Path(vid).is_file():
        raise HTTPException(404, "video not ready")
    return FileResponse(vid, media_type="video/mp4", filename="final.mp4")


# WeChat / messaging webhook style
class ChatIn(BaseModel):
    text: str
    compose: bool = True
    max_scenes: int = 3


@app.post("/api/chat")
def chat_trigger(body: ChatIn) -> dict[str, Any]:
    """Accept phrases like: 科普一下 TCP三次握手 / 状态 / review."""
    text = body.text.strip()
    if text in ("状态", "status", "review"):
        with JOBS_LOCK:
            items = sorted(JOBS.values(), key=lambda j: j.get("created_at", 0), reverse=True)[:5]
        lines = []
        for j in items:
            lines.append(f"- {j['id'][:6]} {j.get('topic')} → {j.get('status')} ({j.get('step')})")
        return {"reply": "最近任务：\n" + ("\n".join(lines) if lines else "暂无"), "jobs": items}

    m = re.match(r"^(?:科普一下|科普|讲讲|动画讲解)\s*(.+)$", text)
    topic = m.group(1).strip() if m else text
    if len(topic) < 2:
        return {"reply": "用法：科普一下 TCP三次握手"}

    created = create_job(
        CreateJob(topic=topic, compose=body.compose, max_scenes=body.max_scenes)
    )
    return {
        "reply": f"已开始生成「{created['topic']}」\n任务 ID: {created['id']}\n稍后打开 http://localhost:8765 查看进度",
        "job": created,
    }


INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>TechAnim · 技术科普动画</title>
<style>
  :root {
    --bg: #0b0f14; --panel: #121a24; --line: #243044; --text: #e8eef7;
    --muted: #8b9bb4; --p: #58c4dd; --s: #83c167; --a: #ffd93d; --w: #ff6b6b;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: ui-sans-serif, system-ui, "PingFang SC", "Hiragino Sans GB", sans-serif;
    background: radial-gradient(1200px 600px at 10% -10%, #16324a 0%, transparent 50%),
                radial-gradient(900px 500px at 100% 0%, #1a2e22 0%, transparent 45%), var(--bg);
    color: var(--text); min-height: 100vh;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 28px 18px 60px; }
  h1 { font-size: 1.55rem; margin: 0 0 6px; letter-spacing: .02em; }
  .sub { color: var(--muted); margin-bottom: 22px; line-height: 1.5; }
  .card {
    background: color-mix(in srgb, var(--panel) 92%, black);
    border: 1px solid var(--line); border-radius: 16px; padding: 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,.35);
  }
  label { display:block; font-size: .85rem; color: var(--muted); margin-bottom: 6px; }
  input[type=text], textarea, select {
    width: 100%; background: #0b1018; border: 1px solid var(--line); color: var(--text);
    border-radius: 10px; padding: 12px 14px; font-size: 1rem; outline: none;
  }
  input:focus, textarea:focus { border-color: var(--p); }
  .row { display:flex; flex-wrap:wrap; gap: 12px; margin-top: 12px; align-items: center; }
  .row > * { flex: 1; min-width: 140px; }
  .checks { display:flex; gap: 16px; align-items:center; color: var(--muted); font-size: .9rem; }
  button {
    appearance:none; border:0; border-radius: 10px; padding: 12px 18px; font-weight: 700;
    cursor: pointer; background: linear-gradient(135deg, var(--p), #3aa8c4); color: #042029;
  }
  button.secondary { background: #243044; color: var(--text); font-weight: 600; }
  button:disabled { opacity: .5; cursor: not-allowed; }
  .hint { font-size: .8rem; color: var(--muted); margin-top: 10px; }
  .status {
    margin-top: 18px; padding: 14px; border-radius: 12px; background: #0b1018;
    border: 1px solid var(--line); font-family: ui-monospace, Menlo, monospace; font-size: .82rem;
    white-space: pre-wrap; color: var(--muted); min-height: 72px;
  }
  .status.ok { border-color: #2f5d3f; color: var(--s); }
  .status.err { border-color: #6b2d2d; color: var(--w); }
  .status.run { border-color: #2a4a5e; color: var(--p); }
  .jobs { margin-top: 22px; }
  .job {
    display:flex; justify-content: space-between; gap: 12px; align-items: center;
    padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; margin-top: 8px;
    background: #0f1520;
  }
  .job b { font-size: .95rem; }
  .pill {
    font-size: .72rem; padding: 3px 8px; border-radius: 999px; background: #1c2a3d; color: var(--muted);
  }
  .pill.done { background: #1c3a2a; color: var(--s); }
  .pill.failed { background: #3a1c1c; color: var(--w); }
  .pill.running, .pill.queued { background: #1a2f40; color: var(--p); }
  a { color: var(--p); }
  .actions { display:flex; gap: 8px; flex-wrap: wrap; }
  .foot { margin-top: 28px; color: var(--muted); font-size: .78rem; }
</style>
</head>
<body>
<div class="wrap">
  <h1>TechAnim · 技术科普动画</h1>
  <p class="sub">基于 OpenMAIC 互动课堂 + 仿真模板 + 豆包旁白成片。<br/>
  也可以发：<code>科普一下 TCP三次握手</code></p>

  <div class="card">
    <label for="topic">主题 / 指令</label>
    <input id="topic" type="text" placeholder="例如：Transformer Attention / 科普一下 区块链哈希" />
    <div class="row">
      <div>
        <label for="audience">受众</label>
        <input id="audience" type="text" value="工程师与技术爱好者" />
      </div>
      <div>
        <label for="max">成片场景数（0=全部）</label>
        <input id="max" type="text" value="3" />
      </div>
    </div>
    <div class="row" style="margin-top:14px">
      <div class="checks">
        <label><input type="checkbox" id="compose" checked /> 合成 final.mp4（豆包 TTS）</label>
      </div>
      <div style="flex:0">
        <button id="go">开始生成</button>
      </div>
    </div>
    <p class="hint">依赖本机 OpenMAIC :3000 与 FlClash 代理。生成可能需要数分钟。</p>
    <div id="status" class="status">就绪。</div>
  </div>

  <div class="jobs">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2 style="font-size:1rem;margin:0">任务</h2>
      <button class="secondary" id="refresh" type="button">刷新</button>
    </div>
    <div id="list"></div>
  </div>

  <p class="foot">TechAnim P4 · API: POST /api/jobs · POST /api/chat · OpenMAIC http://localhost:3000</p>
</div>
<script>
const $ = (id) => document.getElementById(id);
let pollTimer = null;
let activeId = null;

function setStatus(text, cls='') {
  const el = $('status');
  el.textContent = text;
  el.className = 'status' + (cls ? ' ' + cls : '');
}

async function createJob() {
  let topic = $('topic').value.trim();
  if (!topic) { setStatus('请输入主题', 'err'); return; }
  const maxScenes = parseInt($('max').value || '0', 10) || 0;
  $('go').disabled = true;
  setStatus('提交中…', 'run');
  try {
    const r = await fetch('/api/jobs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        topic,
        audience: $('audience').value.trim() || '工程师与技术爱好者',
        compose: $('compose').checked,
        max_scenes: maxScenes,
      })
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || JSON.stringify(j));
    activeId = j.id;
    setStatus(`已创建任务 ${j.id} · ${j.topic}`, 'run');
    poll(j.id);
    loadJobs();
  } catch (e) {
    setStatus('失败: ' + e.message, 'err');
  } finally {
    $('go').disabled = false;
  }
}

async function poll(id) {
  if (pollTimer) clearInterval(pollTimer);
  const tick = async () => {
    try {
      const r = await fetch('/api/jobs/' + id);
      const j = await r.json();
      setStatus(`[${j.status}/${j.step}] ${j.message || ''}\\n${j.job_dir || ''}`, j.status === 'done' ? 'ok' : j.status === 'failed' ? 'err' : 'run');
      if (j.status === 'done' || j.status === 'failed') {
        clearInterval(pollTimer);
        pollTimer = null;
        loadJobs();
      }
    } catch (e) {
      setStatus('轮询失败: ' + e.message, 'err');
    }
  };
  await tick();
  pollTimer = setInterval(tick, 2500);
}

async function loadJobs() {
  const r = await fetch('/api/jobs');
  const data = await r.json();
  const box = $('list');
  box.innerHTML = '';
  (data.jobs || []).forEach(j => {
    const div = document.createElement('div');
    div.className = 'job';
    const left = document.createElement('div');
    left.innerHTML = `<b>${j.topic}</b><div style="color:var(--muted);font-size:.78rem;margin-top:4px">${j.id} · ${j.step || ''}</div>`;
    const right = document.createElement('div');
    right.className = 'actions';
    const pill = document.createElement('span');
    pill.className = 'pill ' + (j.status || '');
    pill.textContent = j.status;
    right.appendChild(pill);
    if (j.status === 'done') {
      const a1 = document.createElement('a');
      a1.href = '/api/jobs/' + j.id + '/video';
      a1.textContent = '视频';
      a1.target = '_blank';
      right.appendChild(a1);
      const a2 = document.createElement('a');
      a2.href = '#';
      a2.textContent = '详情';
      a2.onclick = (e) => { e.preventDefault(); activeId=j.id; poll(j.id); };
      right.appendChild(a2);
    }
    div.appendChild(left);
    div.appendChild(right);
    box.appendChild(div);
  });
  if (!(data.jobs || []).length) {
    box.innerHTML = '<p style="color:var(--muted);font-size:.9rem">暂无任务</p>';
  }
}

$('go').onclick = createJob;
$('topic').addEventListener('keydown', (e) => { if (e.key === 'Enter') createJob(); });
$('refresh').onclick = loadJobs;
loadJobs();
fetch('/api/health').then(r=>r.json()).then(h => {
  if (!h.openmaic) setStatus('警告：OpenMAIC :3000 不可用，请先启动 OpenMAIC', 'err');
}).catch(()=>{});
</script>
</body>
</html>
"""
