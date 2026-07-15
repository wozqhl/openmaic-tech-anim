"""Generate Manim CE scripts from OpenMAIC outlines / tech plan."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PALETTE = {
    "BG": "#1C1C1C",
    "PRIMARY": "#58C4DD",
    "SECONDARY": "#83C167",
    "ACCENT": "#FFFF00",
    "WARN": "#FF6B6B",
    "MUTED": "#888888",
}


def _slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", s.strip())
    return s.strip("_")[:40] or "scene"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _manim_hint(outline: dict[str, Any]) -> str:
    for kp in outline.get("keyPoints") or []:
        if isinstance(kp, str) and kp.strip().startswith("[Manim]"):
            return kp.replace("[Manim]", "").strip()
    desc = outline.get("description") or outline.get("title") or "visual explanation"
    return f"Explain: {desc}"


def generate_manim_project(
    *,
    course_title: str,
    outlines: list[dict[str, Any]],
    out_dir: Path,
    topic: str,
) -> Path:
    """Write plan.md + script.py under out_dir. Returns script path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / "plan.md"
    script_path = out_dir / "script.py"

    # plan.md
    lines = [
        f"# {course_title or topic}",
        "",
        f"**Topic:** {topic}",
        "",
        "## Narrative arc",
        "Hook → Core structure → Mechanism animation → Compare → Apply → Pitfalls",
        "",
        "## Scenes",
        "",
    ]
    for i, o in enumerate(outlines, 1):
        lines.append(f"### Scene {i}: {o.get('title', f'Scene{i}')}")
        lines.append(f"- type: `{o.get('type', 'slide')}`")
        lines.append(f"- objective: {o.get('teachingObjective', '')}")
        lines.append(f"- manim: {_manim_hint(o)}")
        kps = o.get("keyPoints") or []
        if kps:
            lines.append("- key points:")
            for kp in kps[:6]:
                lines.append(f"  - {kp}")
        lines.append("")
    plan_path.write_text("\n".join(lines), encoding="utf-8")

    # script.py — one Scene class per outline
    scenes_code: list[str] = []
    class_names: list[str] = []
    for i, o in enumerate(outlines, 1):
        title = o.get("title") or f"Scene {i}"
        cls = f"Scene{i}_{_slug(title).replace('-', '_')}"
        # Python class name must start with letter and be ascii-ish
        cls = re.sub(r"[^0-9A-Za-z_]", "", cls)
        if not cls[0].isalpha():
            cls = f"Scene{i}"
        class_names.append(cls)
        kps = [str(x) for x in (o.get("keyPoints") or [])[:4]]
        hint = _manim_hint(o)
        kp_lines = "\n".join(
            f'            Text("{_escape(kp[:48])}", font_size=22, color=SECONDARY, font=MONO),'
            for kp in kps
        ) or '            Text("(key points)", font_size=22, color=MUTED, font=MONO),'
        scenes_code.append(
            f'''
class {cls}(Scene):
    def construct(self):
        self.camera.background_color = BG
        title = Text("{_escape(title[:36])}", font_size=40, color=PRIMARY, weight=BOLD, font=MONO)
        title.to_edge(UP, buff=0.6)
        subtitle = Text("{_escape(hint[:50])}", font_size=22, color=MUTED, font=MONO)
        subtitle.next_to(title, DOWN, buff=0.35)

        # Abstract mechanism visual: nodes + flow
        n1 = RoundedRectangle(corner_radius=0.15, width=2.2, height=1.0, color=PRIMARY)
        n2 = RoundedRectangle(corner_radius=0.15, width=2.2, height=1.0, color=SECONDARY)
        n3 = RoundedRectangle(corner_radius=0.15, width=2.2, height=1.0, color=ACCENT)
        t1 = Text("Input", font_size=20, font=MONO, color=PRIMARY)
        t2 = Text("Process", font_size=20, font=MONO, color=SECONDARY)
        t3 = Text("Result", font_size=20, font=MONO, color=ACCENT)
        g1 = VGroup(n1, t1); t1.move_to(n1)
        g2 = VGroup(n2, t2); t2.move_to(n2)
        g3 = VGroup(n3, t3); t3.move_to(n3)
        g1.shift(LEFT * 3.5 + DOWN * 0.5)
        g2.shift(DOWN * 0.5)
        g3.shift(RIGHT * 3.5 + DOWN * 0.5)
        a1 = Arrow(g1.get_right(), g2.get_left(), buff=0.15, color=PRIMARY)
        a2 = Arrow(g2.get_right(), g3.get_left(), buff=0.15, color=SECONDARY)

        bullets = VGroup(
{kp_lines}
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        bullets.scale(0.85)
        bullets.to_edge(DOWN, buff=0.5)

        self.play(Write(title), run_time=1.2)
        self.play(FadeIn(subtitle), run_time=0.6)
        self.wait(0.6)
        self.play(FadeIn(g1), run_time=0.5)
        self.play(GrowArrow(a1), FadeIn(g2), run_time=0.8)
        self.play(GrowArrow(a2), FadeIn(g3), run_time=0.8)
        self.play(g2.animate.set_color(ACCENT), run_time=0.6)
        self.wait(0.5)
        self.play(LaggedStart(*[FadeIn(b, shift=UP*0.1) for b in bullets], lag_ratio=0.15))
        self.wait(1.5)
        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)
'''
        )

    script = f'''"""
Auto-generated tech explainer for: {topic}
Course: {course_title}
Render draft:
  manim -ql script.py {" ".join(class_names)}
"""
from manim import *

BG = "{PALETTE['BG']}"
PRIMARY = "{PALETTE['PRIMARY']}"
SECONDARY = "{PALETTE['SECONDARY']}"
ACCENT = "{PALETTE['ACCENT']}"
WARN = "{PALETTE['WARN']}"
MUTED = "{PALETTE['MUTED']}"
MONO = "Menlo"

{"".join(scenes_code)}
'''
    script_path.write_text(script, encoding="utf-8")

    concat = out_dir / "concat.txt"
    # filled after render; placeholder
    concat.write_text(
        "# After manim -ql, list scene mp4s here for ffmpeg concat\n",
        encoding="utf-8",
    )
    return script_path
