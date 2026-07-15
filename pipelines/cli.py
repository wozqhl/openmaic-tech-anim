#!/usr/bin/env python3
"""TechAnim CLI — plan / gen / render / compose tech popular-science animations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipelines.classroom.client import OpenMAICClient
from pipelines.classroom.offline import offline_outlines
from pipelines.manim.generator import generate_manim_project, outlines_to_vo_scripts
from pipelines.compose.narration import write_narration
from pipelines.simulations.catalog import (
    list_templates,
    match_templates,
    copy_matched_templates,
)


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s.strip())
    return s.strip("-")[:48] or "topic"


def load_prompt(topic: str, audience: str = "工程师与技术爱好者") -> str:
    tpl = (ROOT / "templates/prompts/tech_explainer.md").read_text(encoding="utf-8")
    return tpl.format(topic=topic, audience=audience)


def cmd_plan(args: argparse.Namespace) -> int:
    topic = args.topic
    out = Path(args.output or ROOT / "output" / f"plan_{_slug(topic)}")
    out.mkdir(parents=True, exist_ok=True)
    req = load_prompt(topic, args.audience)
    (out / "requirement.md").write_text(req, encoding="utf-8")
    (out / "plan.md").write_text(
        f"# Plan: {topic}\n\nAudience: {args.audience}\n\n"
        f"See requirement.md for full OpenMAIC prompt wrapper.\n",
        encoding="utf-8",
    )
    print(f"Wrote plan → {out}")
    return 0



# (script, vo_json, optional storyboard_json)
TOPIC_TEMPLATES = {
    "diffusion": ("templates/manim/diffusion_explainer.py", "templates/manim/diffusion_vo.json", "templates/manim/diffusion_storyboard.json"),
    "扩散": ("templates/manim/diffusion_explainer.py", "templates/manim/diffusion_vo.json", "templates/manim/diffusion_storyboard.json"),
    "attention": ("templates/manim/attention_explainer.py", "templates/manim/attention_vo.json", "templates/manim/attention_storyboard.json"),
    "transformer": ("templates/manim/attention_explainer.py", "templates/manim/attention_vo.json", "templates/manim/attention_storyboard.json"),
    "注意力": ("templates/manim/attention_explainer.py", "templates/manim/attention_vo.json", "templates/manim/attention_storyboard.json"),
    "自注意力": ("templates/manim/attention_explainer.py", "templates/manim/attention_vo.json", "templates/manim/attention_storyboard.json"),
    "tcp": ("templates/manim/tcp_handshake.py", "templates/manim/tcp_handshake_vo.json", None),
    "三次握手": ("templates/manim/tcp_handshake.py", "templates/manim/tcp_handshake_vo.json", None),
    "握手": ("templates/manim/tcp_handshake.py", "templates/manim/tcp_handshake_vo.json", None),
    "syn": ("templates/manim/tcp_handshake.py", "templates/manim/tcp_handshake_vo.json", None),
    "http2": ("templates/manim/http2_mux.py", "templates/manim/http2_mux_vo.json", "templates/manim/http2_mux_storyboard.json"),
    "http/2": ("templates/manim/http2_mux.py", "templates/manim/http2_mux_vo.json", "templates/manim/http2_mux_storyboard.json"),
    "多路复用": ("templates/manim/http2_mux.py", "templates/manim/http2_mux_vo.json", "templates/manim/http2_mux_storyboard.json"),
    "kv cache": ("templates/manim/kv_cache.py", "templates/manim/kv_cache_vo.json", "templates/manim/kv_cache_storyboard.json"),
    "kvcache": ("templates/manim/kv_cache.py", "templates/manim/kv_cache_vo.json", "templates/manim/kv_cache_storyboard.json"),
    "kv 缓存": ("templates/manim/kv_cache.py", "templates/manim/kv_cache_vo.json", "templates/manim/kv_cache_storyboard.json"),
    "缓存": ("templates/manim/kv_cache.py", "templates/manim/kv_cache_vo.json", "templates/manim/kv_cache_storyboard.json"),
}


def _maybe_apply_topic_template(topic: str, job_dir: Path) -> None:
    """Copy curated Manim + VO (+ optional storyboard) for known topics."""
    import shutil
    low = topic.lower()
    for key, pack in TOPIC_TEMPLATES.items():
        if key in low or key in topic:
            if isinstance(pack, tuple):
                script_rel = pack[0]
                vo_rel = pack[1] if len(pack) > 1 else None
                sb_rel = pack[2] if len(pack) > 2 else None
            else:
                script_rel, vo_rel, sb_rel = pack, None, None
            src = ROOT / script_rel
            if not src.exists():
                continue
            dest_dir = job_dir / "manim"
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / "script.py")
            if vo_rel:
                vo_src = ROOT / vo_rel
                if vo_src.exists():
                    shutil.copy2(vo_src, dest_dir / vo_src.name)
                    shutil.copy2(vo_src, dest_dir / "topic_vo.json")
            if sb_rel:
                sb_src = ROOT / sb_rel
                if sb_src.exists():
                    shutil.copy2(sb_src, dest_dir / "storyboard.json")
            print(f"     applied topic template: {script_rel}")
            return

def cmd_gen(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    base = os.getenv("OPENMAIC_BASE_URL", "http://127.0.0.1:3000")
    model = os.getenv("OPENMAIC_MODEL", "grok:grok-4.5")
    client = OpenMAICClient(base_url=base, model=model, access_code=os.getenv("OPENMAIC_ACCESS_CODE"))

    print(f"[1/6] Health check {base} ...")
    health = client.health()
    print("     ", health)
    print(f"[2/6] Verify model {model} ...")
    try:
        ver = client.verify_model()
        print("     ", ver)
        if not ver.get("success"):
            print("     warning: model verify not success, continue anyway:", ver, file=sys.stderr)
    except Exception as e:
        print("     warning: model verify failed, continue anyway:", e, file=sys.stderr)

    topic = args.topic
    requirement = load_prompt(topic, args.audience)
    job_dir = Path(args.output or ROOT / "output" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slug(topic)}")
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "requirement.md").write_text(requirement, encoding="utf-8")

    print("[3/6] Streaming outlines from OpenMAIC ...")
    offline = bool(getattr(args, "offline", False))
    result = None
    if not offline:
        try:
            result = client.stream_outlines(requirement, language=args.language, interactive_mode=True)
            if not (result.get("outlines") or []):
                raise RuntimeError("empty outlines from OpenMAIC")
        except Exception as e:
            print(f"     OpenMAIC gen failed ({e}); falling back to offline outlines", file=sys.stderr)
            offline = True
    if offline or result is None:
        result = offline_outlines(topic)
        result["requirementNote"] = "offline fallback"
        print("     mode=OFFLINE template outlines")
    client.save_outlines(result, job_dir / "classroom" / "outlines.json")
    print(f"     title={result.get('courseTitle')!r} scenes={len(result.get('outlines') or [])} offline={bool(result.get('offline'))}")

    print("[4/6] Manim script + plan ...")
    script = generate_manim_project(
        course_title=result.get("courseTitle") or topic,
        outlines=result.get("outlines") or [],
        out_dir=job_dir / "manim",
        topic=topic,
    )
    print(f"     {script}")
    _maybe_apply_topic_template(topic, job_dir)
    # Auto VO scripts for beat-aligned compose (curated topic_vo wins if present)
    vo_path = job_dir / "manim" / "topic_vo.json"
    if not vo_path.exists():
        try:
            vos = outlines_to_vo_scripts(result.get("outlines") or [])
            vo_path.write_text(json.dumps(vos, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"     auto VO → {vo_path} ({len(vos)} scenes)")
        except Exception as e:
            print(f"     auto VO skipped: {e}")

    print("[5/6] Narration ...")
    nar = write_narration(
        course_title=result.get("courseTitle") or topic,
        outlines=result.get("outlines") or [],
        path=job_dir / "narration.md",
        language_directive=result.get("languageDirective") or "",
    )
    print(f"     {nar}")

    print("[6/6] Match interactive simulation templates ...")
    matches = match_templates(topic, result.get("outlines") or [], top_k=3)
    sim_paths = copy_matched_templates(matches, job_dir / "simulations")
    for m in matches:
        print(f"     - {m.get('id')}: {m.get('name')}")
    if not matches:
        print("     (no template matched; see `python -m pipelines.cli sims`)")

    sim_lines = "\n".join(f"  - `{p.name}`" for p in sim_paths) or "  - (none)"
    (job_dir / "README.md").write_text(
        f"# {result.get('courseTitle') or topic}\n\n"
        f"- OpenMAIC UI: {base}\n"
        f"- Outlines: `classroom/outlines.json`\n"
        f"- Manim: `manim/script.py`\n"
        f"- Narration: `narration.md`\n"
        f"- Simulations: `simulations/index.html`\n{sim_lines}\n"
        f"- Compose video: `python -m pipelines.cli compose {job_dir}`\n"
        f"- Model: `{model}`\n",
        encoding="utf-8",
    )
    print(f"\nDone → {job_dir}")
    if getattr(args, "compose", False):
        print("\n[compose] auto after gen ...")
        class _A:
            pass
        a = _A()
        a.job = str(job_dir)
        a.max_scenes = int(getattr(args, "max_scenes", 0) or 0)
        a.beats = bool(getattr(args, "beats", False))
        a.no_subs = False
        a.vo_json = None
        a.voice = None
        a.tts_provider = None
        a.with_manim = bool(getattr(args, "with_manim", False))
        a.quality = None
        rc = cmd_compose(a)
        if rc != 0:
            return rc
    else:
        print("Next: python -m pipelines.cli compose <job_dir> [--max-scenes 2]")
    return 0


def render_manim_job(job: Path, quality: str = "ql", max_scenes: int = 0) -> list[Path]:
    """Render all Scene* classes in job/manim/script.py into job/manim/media/."""
    import re
    import shutil
    import subprocess

    script = job / "manim" / "script.py"
    if not script.exists():
        print("  no manim/script.py; skip")
        return []
    manim = shutil.which("manim") or str(ROOT / ".venv/bin/manim")
    if not Path(manim).exists():
        print("  manim binary missing; skip")
        return []
    names = re.findall(r"^class\s+(\w+)\s*\(", script.read_text(encoding="utf-8"), re.M)
    if max_scenes and max_scenes > 0:
        names = names[:max_scenes]
    if not names:
        print("  no Scene classes found")
        return []
    flag = {"ql": "-ql", "qm": "-qm", "qh": "-qh"}.get(quality, "-ql")
    media_dir = job / "manim" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = (
        "/opt/homebrew/lib/pkgconfig:/opt/homebrew/opt/cairo/lib/pkgconfig:"
        + env.get("PKG_CONFIG_PATH", "")
    )
    env["PATH"] = str(ROOT / ".venv/bin") + ":" + env.get("PATH", "")
    cmd = [manim, flag, "--disable_caching", script.name, *names]
    print("  $", " ".join(cmd[:6]), f"... ({len(names)} scenes)")
    rc = subprocess.call(cmd, cwd=str(script.parent), env=env)
    if rc != 0:
        print(f"  manim exit {rc}", file=sys.stderr)
    # collect mp4s into media/
    outs = []
    for mp4 in sorted((job / "manim").rglob("*.mp4")):
        if "partial_movie_files" in mp4.parts:
            continue
        dest = media_dir / mp4.name
        if mp4.resolve() != dest.resolve():
            shutil.copy2(mp4, dest)
        outs.append(dest)
    # also project-root media from manim default
    root_media = ROOT / "media" / "videos"
    if root_media.exists():
        for mp4 in sorted(root_media.rglob("*.mp4")):
            if "partial_movie_files" in mp4.parts:
                continue
            dest = media_dir / mp4.name
            if not dest.exists():
                shutil.copy2(mp4, dest)
            if dest not in outs:
                outs.append(dest)
    print(f"  manim clips: {len(outs)}")
    return outs



def cmd_sims(args: argparse.Namespace) -> int:
    if args.topic:
        matches = match_templates(args.topic, top_k=args.top_k)
        print(f"Matches for {args.topic!r}:")
        for m in matches:
            print(f"  [{m['id']}] {m['name']}  tags={','.join(m.get('tags') or [])}")
            print(f"      {m.get('description')}")
            print(f"      file: templates/simulations/{m['file']}")
        if not matches:
            print("  (none)")
        if args.copy_to:
            dest = Path(args.copy_to)
            paths = copy_matched_templates(matches, dest)
            print(f"Copied {len(paths)} → {dest}")
        return 0

    print("Available simulation templates:")
    for m in list_templates():
        print(f"  [{m['id']}] {m['name']}")
        print(f"      tags: {', '.join(m.get('tags') or [])}")
        print(f"      {m.get('description')}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    script = Path(args.script).resolve()
    if not script.exists():
        print(f"missing {script}", file=sys.stderr)
        return 1
    quality = args.quality or os.getenv("MANIM_QUALITY", "ql")
    flag = {"ql": "-ql", "qm": "-qm", "qh": "-qh"}.get(quality, "-ql")
    import re
    import shutil
    import subprocess

    manim = shutil.which("manim") or str(ROOT / ".venv/bin/manim")
    if not Path(manim).exists():
        print(
            "manim not installed. pip install manim (cairo already on this machine).",
            file=sys.stderr,
        )
        return 1
    scenes = list(args.scenes or [])
    if not scenes:
        names = re.findall(r"^class\s+(\w+)\s*\(", script.read_text(encoding="utf-8"), re.M)
        scenes = names[:1]
        if scenes:
            print(f"auto scene: {scenes[0]}")
    media_dir = script.parent / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    cmd = [manim, flag, "--disable_caching", "-o", "", str(script), *scenes]
    # force media under script parent
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = "/opt/homebrew/lib/pkgconfig:/opt/homebrew/opt/cairo/lib/pkgconfig:" + env.get("PKG_CONFIG_PATH", "")
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(script.parent), env=env)


def cmd_compose(args: argparse.Namespace) -> int:
    args.subs = not bool(getattr(args, "no_subs", False))
    """Doubao TTS + ffmpeg slide (or manim clips) → final.mp4."""
    from pipelines.compose.tts import write_scene_narration_audio
    from pipelines.compose.video import assemble_final

    load_dotenv(ROOT / ".env")
    job = Path(args.job)
    if not job.is_dir():
        print(f"job dir not found: {job}", file=sys.stderr)
        return 1
    outlines_path = job / "classroom" / "outlines.json"
    if not outlines_path.exists():
        print(f"missing {outlines_path}", file=sys.stderr)
        return 1
    data = json.loads(outlines_path.read_text(encoding="utf-8"))
    outlines = data.get("outlines") or []
    if not outlines:
        print("no outlines", file=sys.stderr)
        return 1
    if args.max_scenes and args.max_scenes > 0:
        outlines = outlines[: args.max_scenes]

    base = os.getenv("OPENMAIC_BASE_URL", "http://127.0.0.1:3000")
    voice = args.voice or os.getenv("TTS_VOICE", "zh_female_vv_uranus_bigtts")
    provider = args.tts_provider or os.getenv("TTS_PROVIDER", "doubao-tts")

    if getattr(args, "with_manim", False):
        q = args.quality or os.getenv("MANIM_QUALITY", "ql")
        print(f"[0/3] Manim render quality={q} ...")
        render_manim_job(job, quality=q, max_scenes=args.max_scenes or 0)

    vo_scripts = None
    vo_json = getattr(args, "vo_json", None)
    if not vo_json:
        # Prefer standardized topic_vo, then any curated *_vo.json
        cands = [
            job / "manim" / "topic_vo.json",
            job / "manim" / "diffusion_vo.json",
            job / "manim" / "attention_vo.json",
            job / "manim" / "tcp_handshake_vo.json",
            job / "manim" / "http2_mux_vo.json",
            job / "manim" / "kv_cache_vo.json",
        ]
        manim_dir = job / "manim"
        if manim_dir.exists():
            cands.extend(sorted(manim_dir.glob("*_vo.json")))
        for c in cands:
            if Path(c).exists():
                vo_json = c
                break
    if vo_json and Path(vo_json).exists():
        raw = json.loads(Path(vo_json).read_text(encoding="utf-8"))
        # preserve scene order by sorted keys Scene1.. or list values in order
        if isinstance(raw, list):
            vo_scripts = raw
        elif isinstance(raw, dict):
            # Scene1_*, Scene2_* numeric order
            def sk(k: str):
                m = re.search(r"(\d+)", k)
                return (int(m.group(1)) if m else 999, k)
            keys = sorted(raw.keys(), key=sk)
            vo_scripts = [raw[k] for k in keys]
        print(f"     using VO scripts from {vo_json} ({len(vo_scripts or [])})")
    else:
        # Fallback: build VO from outlines so beats/storyboard still work
        try:
            vo_scripts = outlines_to_vo_scripts(outlines)
            print(f"     auto VO from outlines ({len(vo_scripts)} scenes)")
        except Exception as e:
            print(f"     VO fallback skipped: {e}")
    srt_paths = None
    beat_rows = None
    print(f"[1/3] TTS ({provider}/{voice}) for {len(outlines)} scenes ...")
    try:
        # Prefer beat mode when VO scripts exist (better A/V + subtitles)
        use_beats = bool(getattr(args, "beats", False)) or bool(vo_scripts)
        if use_beats and vo_scripts:
            from pipelines.compose.beats import synthesize_beats
            print("     mode=beat-aligned (sentence TTS + SRT)")
            # Align VO length to outline scenes
            if len(vo_scripts) > len(outlines):
                vo_scripts = vo_scripts[: len(outlines)]
            beat_rows = synthesize_beats(
                vo_scripts,
                job / "audio",
                base_url=base,
                provider_id=provider,
                voice=voice,
                speed=float(os.getenv("TTS_SPEED", "1.08")),
            )
            audio_paths = [r["audio"] for r in beat_rows]
            srt_paths = [r["srt"] for r in beat_rows]
        else:
            audio_paths = write_scene_narration_audio(
                outlines,
                job / "audio",
                vo_scripts=vo_scripts,
                base_url=base,
                provider_id=provider,
                voice=voice,
            )
    except Exception as e:
        print(f"TTS failed: {e}", file=sys.stderr)
        return 2

    print("[2/3] Assemble video clips + mux audio ...")
    try:
        use_sb = (not bool(getattr(args, "no_storyboard", False))) and bool(
            getattr(args, "storyboard", True)
        )
        final = assemble_final(
            outlines=outlines,
            audio_paths=audio_paths,
            work_dir=job / "video",
            manim_dir=job / "manim",
            final_name="final.mp4",
            srt_paths=srt_paths,
            burn_subs=bool(getattr(args, "subs", True)),
            beat_rows=beat_rows,  # pass whenever synthesized
            storyboard_path=job / "manim" / "storyboard.json",
            use_storyboard=use_sb,
        )
    except Exception as e:
        print(f"compose failed: {e}", file=sys.stderr)
        return 3

    print(f"[3/3] Done → {final}")
    print(f"     size={final.stat().st_size} bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="tech-anim",
        description="Tech popular-science animation via OpenMAIC + Manim/ffmpeg",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="Write planning files only")
    p_plan.add_argument("topic")
    p_plan.add_argument("--audience", default="工程师与技术爱好者")
    p_plan.add_argument("--output")
    p_plan.set_defaults(func=cmd_plan)

    p_gen = sub.add_parser("gen", help="Generate outlines + manim + narration + sims")
    p_gen.add_argument("topic")
    p_gen.add_argument("--audience", default="工程师与技术爱好者")
    p_gen.add_argument("--language", default="zh-CN")
    p_gen.add_argument("--style", default="tech-explainer")
    p_gen.add_argument("--output")
    p_gen.add_argument("--offline", action="store_true", help="Skip LLM; use template outlines")
    p_gen.add_argument("--beats", action="store_true", help="After gen compose with sentence TTS + subs")
    p_gen.add_argument("--compose", action="store_true", help="After gen, run TTS+video compose")
    p_gen.add_argument("--max-scenes", type=int, default=0, help="With --compose: limit scenes (0=all)")
    p_gen.add_argument("--with-manim", action="store_true", help="With --compose: also render Manim")
    p_gen.set_defaults(func=cmd_gen)

    p_ren = sub.add_parser("render", help="Render manim script (optional)")
    p_ren.add_argument("script")
    p_ren.add_argument("--quality", choices=["ql", "qm", "qh"])
    p_ren.add_argument("scenes", nargs="*")
    p_ren.set_defaults(func=cmd_render)

    p_sims = sub.add_parser("sims", help="List / match interactive HTML simulation templates")
    p_sims.add_argument("topic", nargs="?")
    p_sims.add_argument("--top-k", type=int, default=3)
    p_sims.add_argument("--copy-to")
    p_sims.set_defaults(func=cmd_sims)

    p_comp = sub.add_parser("compose", help="Doubao TTS + ffmpeg → final.mp4")
    p_comp.add_argument("job", help="Path to output/<job> directory")
    p_comp.add_argument("--max-scenes", type=int, default=0, help="0=all; 2 for quick demo")
    p_comp.add_argument("--voice", default=None)
    p_comp.add_argument("--tts-provider", default=None)
    p_comp.add_argument("--with-manim", action="store_true", help="Render Manim scenes before compose")
    p_comp.add_argument("--quality", choices=["ql", "qm", "qh"], default=None)
    p_comp.add_argument("--vo-json", default=None, help="JSON map/list of VO scripts aligned to scenes")
    p_comp.add_argument("--beats", action="store_true", help="Sentence-level TTS + SRT burn-in")
    p_comp.add_argument("--no-subs", action="store_true", help="Disable subtitle burn-in")
    p_comp.set_defaults(func=cmd_compose)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
