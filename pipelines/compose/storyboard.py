"""Storyboard-level A/V sync: map VO beats to Manim visual time ranges.

For each scene:
  - VO is already split into beats with durations (from beats.py)
  - Manim clip is sliced into visual segments by fractional ranges
  - Each visual segment is retimed to match its beat duration
  - Segments concat → scene video, then mux full scene audio + burn SRT

Storyboard JSON (optional, per job manim/storyboard.json or templates):
{
  "Scene1_Hook": [
    {"tag": "open", "t0": 0.0, "t1": 0.35},
    {"tag": "action", "t0": 0.35, "t1": 0.75},
    {"tag": "punch", "t0": 0.75, "t1": 1.0}
  ],
  ...
}

If missing, beats are mapped to equal slices of the manim clip.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd[:8]), "...")
    subprocess.check_call(cmd)


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


def load_storyboard(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if not path or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    return raw


def equal_slices(n: int) -> list[dict[str, Any]]:
    if n <= 0:
        return []
    step = 1.0 / n
    out = []
    for i in range(n):
        out.append({"tag": f"b{i+1}", "t0": i * step, "t1": (i + 1) * step})
    return out


def _slice_retime(
    src: Path,
    *,
    t0: float,
    t1: float,
    target_dur: float,
    out: Path,
) -> None:
    """Extract [t0,t1] seconds from src and retime to target_dur."""
    vdur = max(_ffprobe_duration(src), 0.05)
    start = max(0.0, min(t0, vdur - 0.05))
    end = max(start + 0.05, min(t1, vdur))
    seg = max(end - start, 0.05)
    target_dur = max(target_dur, 0.2)
    # setpts multiplier >1 slows video to fill target_dur
    factor = min(target_dur / seg, 8.0)
    pad = max(0.0, target_dur - seg * factor)
    vf = (
        f"trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS,"
        f"setpts=PTS*{factor:.4f},"
        f"scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,"
        f"tpad=stop_mode=clone:stop_duration={pad:.3f}"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-vf",
            vf,
            "-t",
            f"{target_dur:.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ]
    )


def assemble_scene_storyboard(
    *,
    manim_clip: Path,
    beat_timeline: list[dict[str, Any]],
    scene_audio: Path,
    work_dir: Path,
    scene_idx: int,
    storyboard_slices: list[dict[str, Any]] | None,
    srt_path: Path | None = None,
    burn_subs: bool = True,
) -> Path:
    """
    beat_timeline: [{text,start,end,duration}, ...] from beats.py
    storyboard_slices: [{t0,t1}] as fractions 0..1 of manim duration
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    n = len(beat_timeline)
    if n == 0:
        raise ValueError("empty beat timeline")

    vdur = max(_ffprobe_duration(manim_clip), 0.1)
    slices = storyboard_slices if storyboard_slices and len(storyboard_slices) >= n else equal_slices(n)
    # if more slices than beats, merge trailing; if fewer, equal fallback
    if len(slices) < n:
        slices = equal_slices(n)
    slices = slices[:n]

    seg_paths: list[Path] = []
    for j, (beat, sl) in enumerate(zip(beat_timeline, slices), 1):
        bdur = float(beat.get("duration") or (beat.get("end", 0) - beat.get("start", 0)) or 1.0)
        t0 = float(sl.get("t0", (j - 1) / n)) * vdur
        t1 = float(sl.get("t1", j / n)) * vdur
        out = work_dir / f"s{scene_idx:02d}_seg{j:02d}.mp4"
        _slice_retime(manim_clip, t0=t0, t1=t1, target_dur=bdur, out=out)
        seg_paths.append(out)

    # concat visual segments
    list_file = work_dir / f"s{scene_idx:02d}_concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in seg_paths) + "\n",
        encoding="utf-8",
    )
    silent = work_dir / f"s{scene_idx:02d}_video.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(silent),
        ]
    )

    muxed = work_dir / f"scene_{scene_idx:02d}.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-i",
            str(scene_audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(muxed) if not (srt_path and burn_subs) else str(work_dir / f"scene_{scene_idx:02d}_nosub.mp4"),
        ]
    )
    if srt_path and burn_subs and srt_path.exists():
        nosub = work_dir / f"scene_{scene_idx:02d}_nosub.mp4"
        if not nosub.exists():
            nosub = muxed
        sp = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
        vf = (
            f"subtitles='{sp}':force_style="
            f"'FontName=Hiragino Sans GB,FontSize=18,PrimaryColour=&H00E8EEF7&,"
            f"OutlineColour=&H80000000&,BorderStyle=3,Outline=1,Shadow=0,MarginV=28'"
        )
        try:
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(nosub),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "copy",
                    str(muxed),
                ]
            )
        except Exception as e:
            print(f"  storyboard subtitle burn failed: {e}")
            if nosub != muxed and nosub.exists():
                nosub.replace(muxed)
    return muxed


def resolve_scene_storyboard(
    board: dict[str, list[dict[str, Any]]],
    manim_path: Path,
    n_beats: int,
) -> list[dict[str, Any]]:
    """Pick storyboard entry by manim stem / Scene prefix."""
    stem = manim_path.stem
    if stem in board:
        return board[stem]
    # fuzzy: Scene1_* keys
    for k, v in board.items():
        if stem.startswith(k) or k.startswith(stem[:8]):
            return v
    # numeric Scene1
    import re

    m = re.match(r"(Scene\d+)", stem)
    if m:
        for k, v in board.items():
            if k.startswith(m.group(1)):
                return v
    return equal_slices(n_beats)
