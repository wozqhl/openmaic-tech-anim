"""TTS via OpenMAIC /api/generate/tts (Doubao server-side key)."""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import httpx


def _spoken_from_outline(outline: dict[str, Any], max_chars: int = 280) -> str:
    parts: list[str] = []
    title = outline.get("title") or ""
    if title:
        parts.append(str(title) + "。")
    desc = outline.get("description") or ""
    if desc:
        parts.append(str(desc))
    for kp in outline.get("keyPoints") or []:
        s = str(kp).strip()
        if s.startswith("[Manim]"):
            continue
        parts.append(s + "。")
    text = re.sub(r"\s+", " ", " ".join(parts)).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    return text or "本节讲解。"


def synthesize_via_openmaic(
    text: str,
    *,
    base_url: str = "http://127.0.0.1:3000",
    provider_id: str = "doubao-tts",
    voice: str = "zh_female_vv_uranus_bigtts",
    audio_id: str = "clip",
    speed: float = 1.0,
    timeout: float = 60.0,
) -> tuple[bytes, str]:
    """Returns (audio_bytes, format)."""
    payload = {
        "text": text,
        "audioId": audio_id,
        "ttsProviderId": provider_id,
        "ttsVoice": voice,
        "ttsSpeed": speed,
    }
    with httpx.Client(trust_env=False, timeout=timeout) as c:
        r = c.post(f"{base_url.rstrip('/')}/api/generate/tts", json=payload)
        r.raise_for_status()
        data = r.json()
    body = data.get("data") or data
    if not data.get("success", True) and "base64" not in body:
        raise RuntimeError(f"TTS failed: {data}")
    b64 = body.get("base64")
    fmt = body.get("format") or "mp3"
    if not b64:
        raise RuntimeError(f"TTS missing base64: {data}")
    return base64.b64decode(b64), fmt


def write_scene_narration_audio(
    outlines: list[dict[str, Any]],
    out_dir: Path,
    vo_scripts: list[str] | None = None,
    *,
    base_url: str = "http://127.0.0.1:3000",
    provider_id: str = "doubao-tts",
    voice: str = "zh_female_vv_uranus_bigtts",
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, o in enumerate(outlines, 1):
        text = (vo_scripts[i-1] if vo_scripts and (i-1) < len(vo_scripts) and vo_scripts[i-1] else _spoken_from_outline(o, max_chars=220))
        audio, fmt = synthesize_via_openmaic(
            text,
            base_url=base_url,
            provider_id=provider_id,
            voice=voice,
            audio_id=f"scene_{i}",
        )
        ext = "mp3" if "mp" in fmt.lower() else fmt.lstrip(".")
        path = out_dir / f"scene_{i:02d}.{ext}"
        path.write_bytes(audio)
        # also store text
        (out_dir / f"scene_{i:02d}.txt").write_text(text, encoding="utf-8")
        paths.append(path)
        print(f"  TTS scene {i}: {path.name} ({len(audio)} bytes) text={text[:40]}…")
    return paths
