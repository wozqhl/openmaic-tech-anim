"""Beat-aligned VO: split scripts into sentences, TTS each, concat with timeline."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pipelines.compose.tts import synthesize_via_openmaic


def split_beats(text: str) -> list[str]:
    """Split Chinese/English narration into speakable beats."""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    # split on sentence punctuation, keep non-empty
    parts = re.split(r"(?<=[。！？；;!?])\s*", text)
    beats = [p.strip() for p in parts if p and p.strip()]
    # merge tiny fragments
    merged: list[str] = []
    for b in beats:
        if merged and len(b) < 8:
            merged[-1] = merged[-1] + b
        else:
            merged.append(b)
    return merged or [text]


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out or "0")


def synthesize_beats(
    scripts: list[str],
    out_dir: Path,
    *,
    base_url: str = "http://127.0.0.1:3000",
    provider_id: str = "doubao-tts",
    voice: str = "zh_female_vv_uranus_bigtts",
    speed: float = 1.08,
) -> list[dict[str, Any]]:
    """
    For each scene script:
      - split beats
      - TTS each beat
      - concat to scene_XX.mp3
      - write scene_XX.srt + timeline.json
    Returns list of {scene, audio, duration, beats:[{text,start,end,file}]}
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for i, script in enumerate(scripts, 1):
        beats = split_beats(script)
        beat_files: list[Path] = []
        timeline: list[dict[str, Any]] = []
        t = 0.0
        scene_beat_dir = out_dir / f"beats_{i:02d}"
        scene_beat_dir.mkdir(exist_ok=True)

        for j, beat in enumerate(beats, 1):
            audio, fmt = synthesize_via_openmaic(
                beat,
                base_url=base_url,
                provider_id=provider_id,
                voice=voice,
                audio_id=f"s{i}_b{j}",
                speed=speed,
            )
            ext = "mp3" if "mp" in fmt.lower() else fmt.lstrip(".")
            bp = scene_beat_dir / f"b{j:02d}.{ext}"
            bp.write_bytes(audio)
            dur = _ffprobe_duration(bp)
            timeline.append(
                {
                    "i": j,
                    "text": beat,
                    "start": round(t, 3),
                    "end": round(t + dur, 3),
                    "duration": round(dur, 3),
                    "file": str(bp.name),
                }
            )
            beat_files.append(bp)
            t += dur
            print(f"  beat s{i}/b{j}: {dur:.2f}s  {beat[:36]}…")

        # concat beats → scene audio
        list_file = scene_beat_dir / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{bf.resolve()}'" for bf in beat_files) + "\n",
            encoding="utf-8",
        )
        scene_audio = out_dir / f"scene_{i:02d}.mp3"
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(scene_audio),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # srt
        srt_path = out_dir / f"scene_{i:02d}.srt"

        def ts(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int(round((sec - int(sec)) * 1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_lines = []
        for k, b in enumerate(timeline, 1):
            srt_lines.append(str(k))
            srt_lines.append(f"{ts(b['start'])} --> {ts(b['end'])}")
            srt_lines.append(b["text"])
            srt_lines.append("")
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
        (out_dir / f"scene_{i:02d}.txt").write_text(script, encoding="utf-8")
        (out_dir / f"scene_{i:02d}_timeline.json").write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        total = _ffprobe_duration(scene_audio)
        results.append(
            {
                "scene": i,
                "audio": scene_audio,
                "srt": srt_path,
                "duration": total,
                "beats": timeline,
            }
        )
        print(f"  scene {i}: {total:.2f}s  {len(beats)} beats → {scene_audio.name}")

    (out_dir / "beats_meta.json").write_text(
        json.dumps(
            [
                {
                    "scene": r["scene"],
                    "duration": r["duration"],
                    "beats": len(r["beats"]),
                    "audio": str(r["audio"]),
                    "srt": str(r["srt"]),
                }
                for r in results
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return results
