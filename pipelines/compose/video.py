"""Assemble tech explainer video: slides/manim clips + TTS audio via ffmpeg."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str]) -> None:
    print("  $", " ".join(cmd[:8]), "..." if len(cmd) > 8 else "")
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


def _cjk_fontfile() -> str | None:
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for f in candidates:
        if Path(f).exists():
            return f
    return None


def make_slide_clip(
    *,
    title: str,
    bullets: list[str],
    duration: float,
    out_path: Path,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Generate a dark-theme title+bullets slide video with ffmpeg drawtext."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
            .replace(":", "\\:")
            .replace("'", "\\'")
            .replace("%", "\\%")
            .replace(",", "\\,")
        )

    fontfile = _cjk_fontfile()
    font_opt = f":fontfile={fontfile}" if fontfile else ""

    title_s = esc(title[:36])
    lines = [esc(b[:42]) for b in bullets[:4]]
    filters = [
        f"drawtext=text='{title_s}':fontcolor=0x58C4DD:fontsize=40:x=60:y=80{font_opt}"
    ]
    y = 180
    for line in lines:
        filters.append(
            f"drawtext=text='- {line}':fontcolor=0xE8EEF7:fontsize=26:x=80:y={y}{font_opt}"
        )
        y += 52
    filters.append(
        f"drawtext=text='TechAnim':fontcolor=0x8B9BB4:fontsize=18:x=w-180:y=h-40{font_opt}"
    )
    vf = ",".join(filters)
    dur = max(duration, 1.0)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x1C1C1C:s={width}x{height}:d={dur}:r=30",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-t",
        f"{dur:.2f}",
        str(out_path),
    ]
    _run(cmd)
    return out_path


def mux_av(video: Path, audio: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(out),
    ]
    _run(cmd)
    return out


def find_manim_clips(manim_dir: Path) -> list[Path]:
    """Prefer final Scene*.mp4 under manim/media, exclude partials and stale clips."""
    if not manim_dir.exists():
        return []
    # Preferred class names from script.py
    names: list[str] = []
    script = manim_dir / "script.py"
    if script.exists():
        names = re.findall(r"^class\s+(Scene\w+)\s*\(", script.read_text(encoding="utf-8"), re.M)
    candidates: list[Path] = []
    for c in manim_dir.rglob("*.mp4"):
        if "partial_movie_files" in c.parts:
            continue
        candidates.append(c)
    flat = [c for c in candidates if c.parent.name == "media" and c.name.startswith("Scene")]
    if names and flat:
        by = {c.stem: c for c in flat}
        ordered = [by[n] for n in names if n in by]
        if ordered:
            return ordered
    if flat:
        return sorted(flat, key=lambda p: p.name)
    # next: **/480p*/Scene*.mp4 (or 720p etc.) finals only
    finals = [c for c in candidates if c.name.startswith("Scene") and "videos" in c.parts]
    if finals:
        # dedupe by filename, keep first sorted path
        by_name: dict[str, Path] = {}
        for c in sorted(finals):
            by_name.setdefault(c.name, c)
        return [by_name[k] for k in sorted(by_name)]
    return sorted(candidates)


def assemble_final(
    *,
    outlines: list[dict[str, Any]],
    audio_paths: list[Path],
    work_dir: Path,
    manim_dir: Path | None = None,
    final_name: str = "final.mp4",
    srt_paths: list[Path] | None = None,
    burn_subs: bool = True,
    crossfade: float = 0.35,
    beat_rows: list[dict] | None = None,
    storyboard_path: Path | None = None,
    use_storyboard: bool = True,
) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    manim_clips = find_manim_clips(manim_dir) if manim_dir else []
    from pipelines.compose.storyboard import (
        load_storyboard,
        assemble_scene_storyboard,
        resolve_scene_storyboard,
    )
    board = load_storyboard(storyboard_path) if use_storyboard else {}

    scene_files: list[Path] = []
    for i, o in enumerate(outlines):
        audio = audio_paths[i] if i < len(audio_paths) else None
        dur = _ffprobe_duration(audio) + 0.5 if audio else float(o.get("estimatedDuration") or 8)
        dur = max(3.0, min(dur, 90.0))
        title = str(o.get("title") or f"Scene {i+1}")
        bullets = [
            str(k) for k in (o.get("keyPoints") or []) if not str(k).startswith("[Manim]")
        ][:4]

        slide = clips_dir / f"slide_{i+1:02d}.mp4"
        src_video = manim_clips[i] if i < len(manim_clips) else None

        # Storyboard path: per-beat visual slices aligned to VO beats
        if (
            use_storyboard
            and src_video
            and src_video.exists()
            and beat_rows
            and i < len(beat_rows)
            and beat_rows[i].get("beats")
            and audio
        ):
            srt = Path(srt_paths[i]) if srt_paths and i < len(srt_paths) and srt_paths[i] else None
            slices = resolve_scene_storyboard(board, src_video, len(beat_rows[i]["beats"]))
            try:
                muxed = assemble_scene_storyboard(
                    manim_clip=src_video,
                    beat_timeline=beat_rows[i]["beats"],
                    scene_audio=audio,
                    work_dir=clips_dir / "storyboard",
                    scene_idx=i + 1,
                    storyboard_slices=slices,
                    srt_path=srt,
                    burn_subs=burn_subs,
                )
                scene_files.append(muxed)
                print(f"  storyboard scene {i+1}: {len(beat_rows[i]['beats'])} beats → {muxed.name}")
                continue
            except Exception as e:
                print(f"  storyboard scene {i+1} failed ({e}); fallback retime")
        srt = None
        if srt_paths and i < len(srt_paths) and srt_paths[i] and Path(srt_paths[i]).exists():
            srt = Path(srt_paths[i])

        if src_video and src_video.exists():
            vdur = max(_ffprobe_duration(src_video), 0.1)
            pad = max(0.0, dur - vdur)
            # Smart retime: prefer mild slowdown over long freeze (looks less broken).
            max_slow = 1.55  # cap stretch
            if pad < 0.08:
                vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2"
                cmd = [
                    "ffmpeg", "-y", "-i", str(src_video),
                    "-vf", vf, "-t", f"{dur:.2f}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(slide),
                ]
            else:
                needed = dur / vdur
                if needed <= max_slow:
                    # pure slowdown to fit VO
                    vf = (
                        f"setpts=PTS*{needed:.4f},"
                        f"scale=1280:720:force_original_aspect_ratio=decrease,"
                        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2"
                    )
                    cmd = [
                        "ffmpeg", "-y", "-i", str(src_video),
                        "-vf", vf, "-t", f"{dur:.2f}",
                        "-r", "30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(slide),
                    ]
                else:
                    # slow to cap then freeze remainder
                    slow = max_slow
                    slowed_dur = vdur * slow
                    rest = max(0.0, dur - slowed_dur)
                    vf = (
                        f"setpts=PTS*{slow:.4f},"
                        f"scale=1280:720:force_original_aspect_ratio=decrease,"
                        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
                        f"tpad=stop_mode=clone:stop_duration={rest:.3f}"
                    )
                    cmd = [
                        "ffmpeg", "-y", "-i", str(src_video),
                        "-vf", vf, "-t", f"{dur:.2f}",
                        "-r", "30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(slide),
                    ]
            _run(cmd)
        else:
            make_slide_clip(title=title, bullets=bullets, duration=dur, out_path=slide)

        if audio and audio.exists():
            muxed = clips_dir / f"scene_{i+1:02d}.mp4"
            if srt and burn_subs:
                # re-encode with burned Chinese subtitles (FontName via force_style)
                _ = _cjk_fontfile()  # ensure CJK font present on host; libass picks by FontName
                sp = str(srt.resolve()).replace("\\", "/").replace(":", "\\:")
                vf = (
                    f"subtitles='{sp}':force_style="
                    f"'FontName=Hiragino Sans GB,FontSize=18,PrimaryColour=&H00E8EEF7&,"
                    f"OutlineColour=&H80000000&,BorderStyle=3,Outline=1,Shadow=0,"
                    f"MarginV=28'"
                )
                tmp = clips_dir / f"scene_{i+1:02d}_nosub.mp4"
                mux_av(slide, audio, tmp)
                cmd = [
                    "ffmpeg", "-y", "-i", str(tmp),
                    "-vf", vf,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", str(muxed),
                ]
                try:
                    _run(cmd)
                except Exception as e:
                    print(f"  subtitle burn failed ({e}); using no-sub")
                    tmp.replace(muxed)
            else:
                mux_av(slide, audio, muxed)
            scene_files.append(muxed)
        else:
            scene_files.append(slide)


    list_file = work_dir / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in scene_files) + "\n",
        encoding="utf-8",
    )
    final = work_dir / final_name

    used_xfade = False
    if crossfade and crossfade > 0.05 and len(scene_files) >= 2:
        try:
            _concat_with_xfade(scene_files, final, fade=crossfade)
            used_xfade = True
        except Exception as e:
            print(f"  xfade failed ({e}); falling back to hard cut")
            used_xfade = False

    if not used_xfade:
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
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(final),
            ]
        )

    meta = {
        "scenes": len(scene_files),
        "final": str(final),
        "used_manim_clips": len(manim_clips),
        "font": _cjk_fontfile(),
        "burn_subs": bool(burn_subs and srt_paths),
        "crossfade": crossfade if used_xfade else 0,
        "xfade": used_xfade,
        "storyboard": bool(use_storyboard and beat_rows),
    }
    (work_dir / "compose_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return final


def _concat_with_xfade(scene_files: list[Path], final: Path, fade: float = 0.35) -> None:
    """Soft-cut between scenes with xfade + acrossfade."""
    if len(scene_files) == 1:
        _run(["ffmpeg", "-y", "-i", str(scene_files[0]), "-c", "copy", "-movflags", "+faststart", str(final)])
        return

    durs = [_ffprobe_duration(p) for p in scene_files]
    # ensure each scene longer than fade
    fade = min(fade, min(durs) * 0.4)
    if fade < 0.08:
        raise RuntimeError("fade too small")

    inputs: list[str] = []
    for p in scene_files:
        inputs.extend(["-i", str(p)])

    # Build filter graph
    vlabels = [f"[{i}:v]settb=AVTB,fps=30,format=yuv420p[v{i}]" for i in range(len(scene_files))]
    alabels = [f"[{i}:a]aformat=sample_rates=48000:channel_layouts=mono[a{i}]" for i in range(len(scene_files))]

    # cumulative offset for xfade: sum(prev durations) - fade * n_prev
    fc_parts = vlabels + alabels
    cur_v = "v0"
    cur_a = "a0"
    offset = durs[0] - fade
    for i in range(1, len(scene_files)):
        out_v = f"vx{i}"
        out_a = f"ax{i}"
        fc_parts.append(
            f"[{cur_v}][v{i}]xfade=transition=fade:duration={fade:.3f}:offset={max(offset, 0):.3f}[{out_v}]"
        )
        fc_parts.append(f"[{cur_a}][a{i}]acrossfade=d={fade:.3f}[{out_a}]")
        cur_v, cur_a = out_v, out_a
        if i + 1 < len(scene_files):
            # next offset accumulates remaining timeline length after this xfade
            offset = offset + durs[i] - fade

    filter_complex = ";".join(fc_parts)
    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        f"[{cur_v}]",
        "-map",
        f"[{cur_a}]",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(final),
    ]
    _run(cmd)
