"""OpenMAIC HTTP client for tech-explainer classroom generation."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx


class OpenMAICClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:3000",
        model: str = "grok:grok-4.5",
        access_code: str | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        headers = {"Content-Type": "application/json", "x-model": model}
        if access_code:
            headers["x-access-code"] = access_code
        self._headers = headers

    def health(self) -> dict[str, Any]:
        with httpx.Client(timeout=10.0, trust_env=False) as c:
            r = c.get(f"{self.base_url}/api/health")
            r.raise_for_status()
            return r.json()

    def verify_model(self, model: str | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=60.0, trust_env=False) as c:
            r = c.post(
                f"{self.base_url}/api/verify-model",
                headers=self._headers,
                json={"model": model or self.model},
            )
            r.raise_for_status()
            return r.json()

    def stream_outlines(
        self,
        requirement: str,
        *,
        language: str = "zh-CN",
        interactive_mode: bool = True,
    ) -> dict[str, Any]:
        """Call scene-outlines-stream and collect SSE into a structured result."""
        payload = {
            "requirements": {
                "requirement": requirement,
                "language": language,
                "interactiveMode": interactive_mode,
            }
        }
        outlines: list[dict[str, Any]] = []
        language_directive = ""
        course_title = ""
        errors: list[str] = []
        raw_events: list[dict[str, Any]] = []

        with httpx.Client(timeout=self.timeout, trust_env=False) as c:
            with c.stream(
                "POST",
                f"{self.base_url}/api/generate/scene-outlines-stream",
                headers=self._headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                    else:
                        continue
                    if data_str == "[DONE]":
                        break
                    try:
                        evt = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    raw_events.append(evt)
                    et = evt.get("type")
                    if et == "languageDirective":
                        language_directive = evt.get("data") or ""
                    elif et == "courseTitle":
                        course_title = evt.get("data") or ""
                    elif et == "outline":
                        outlines.append(evt.get("data") or {})
                    elif et == "done":
                        outlines = evt.get("outlines") or outlines
                        language_directive = evt.get("languageDirective") or language_directive
                        course_title = evt.get("courseTitle") or course_title
                    elif et == "error":
                        errors.append(str(evt.get("error") or evt))

        if errors and not outlines:
            raise RuntimeError("; ".join(errors))

        return {
            "courseTitle": course_title,
            "languageDirective": language_directive,
            "outlines": outlines,
            "errors": errors,
            "eventCount": len(raw_events),
        }

    def create_classroom_job(self, requirement: str, **opts: Any) -> dict[str, Any]:
        body = {"requirement": requirement, **opts}
        with httpx.Client(timeout=30.0, trust_env=False) as c:
            r = c.post(
                f"{self.base_url}/api/generate-classroom",
                headers=self._headers,
                json=body,
            )
            # 202 accepted
            if r.status_code not in (200, 202):
                r.raise_for_status()
            return r.json()

    def poll_classroom_job(self, job_id: str, interval: float = 5.0, max_wait: float = 600.0) -> dict[str, Any]:
        deadline = time.time() + max_wait
        with httpx.Client(timeout=30.0, trust_env=False) as c:
            while time.time() < deadline:
                r = c.get(f"{self.base_url}/api/generate-classroom/{job_id}", headers=self._headers)
                r.raise_for_status()
                data = r.json()
                status = (data.get("data") or data).get("status") or data.get("status")
                if status in ("completed", "failed", "error", "success", "done"):
                    return data
                time.sleep(interval)
        raise TimeoutError(f"classroom job {job_id} timed out")

    def save_outlines(self, result: dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
