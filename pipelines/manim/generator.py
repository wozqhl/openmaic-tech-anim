"""Generate Manim CE scripts from OpenMAIC outlines / tech plan.

Produces richer, type-aware scenes (not only title+bullets):
- slide: concept cards + flow
- interactive: state/timeline metaphor
- quiz/game: pitfall callouts
Uses PingFang SC when available for Chinese titles.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PALETTE = {
    "BG": "#0f1419",
    "PRIMARY": "#58C4DD",
    "SECONDARY": "#83C167",
    "ACCENT": "#FFD93D",
    "WARN": "#FF6B6B",
    "MUTED": "#8B9BB4",
}

CJK_FONT = "PingFang SC"
FALLBACK_FONT = "Menlo"


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
    return f"{desc}"[:80]


def _clean_kps(outline: dict[str, Any], n: int = 4) -> list[str]:
    out: list[str] = []
    for x in outline.get("keyPoints") or []:
        s = str(x).strip()
        if s.startswith("[Manim]"):
            continue
        out.append(s[:56])
        if len(out) >= n:
            break
    return out


def _scene_block(
    *,
    cls: str,
    title: str,
    hint: str,
    kps: list[str],
    scene_type: str,
    index: int,
) -> str:
    """Return one Scene class source with type-specific visuals."""
    kp_items = "\n".join(
        f'            Text("{_escape(kp)}", font_size=22, color=SECONDARY, font=FONT),'
        for kp in kps
    ) or '            Text("(要点)", font_size=22, color=MUTED, font=FONT),'

    st = (scene_type or "slide").lower()
    # visual recipe by type + position in arc
    if st in {"interactive", "simulation"} or index == 2:
        body = f'''
        # Timeline / state-machine metaphor
        axis = NumberLine(x_range=[0, 6, 1], length=10, color=MUTED)
        axis.shift(DOWN * 1.8)
        labels = VGroup(
            Text("开始", font_size=18, color=MUTED, font=FONT),
            Text("过程", font_size=18, color=PRIMARY, font=FONT),
            Text("结果", font_size=18, color=SECONDARY, font=FONT),
        )
        labels[0].next_to(axis.n2p(0), DOWN)
        labels[1].next_to(axis.n2p(3), DOWN)
        labels[2].next_to(axis.n2p(6), DOWN)
        dot = Dot(axis.n2p(0), color=ACCENT, radius=0.12)
        card = RoundedRectangle(width=9, height=2.2, corner_radius=0.15,
                                stroke_color=PRIMARY, fill_opacity=0.08, fill_color=PRIMARY)
        card.shift(UP * 0.35)
        bullets = VGroup(
{kp_items}
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).scale(0.9)
        bullets.move_to(card.get_center())

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle), run_time=0.6)
        self.play(Create(axis), FadeIn(labels), run_time=1.0)
        self.play(FadeIn(card), FadeIn(bullets, lag_ratio=0.12), run_time=1.4)
        self.play(dot.animate.move_to(axis.n2p(3)), run_time=1.2)
        self.play(dot.animate.move_to(axis.n2p(6)), card.animate.set_stroke(SECONDARY), run_time=1.2)
        self.wait(1.8)
'''
    elif st in {"quiz", "game"} or "坑" in title or "误区" in title:
        body = f'''
        # Pitfalls board
        cards = VGroup()
        colors = [WARN, ACCENT, PRIMARY]
        texts = [{", ".join(repr(k[:28]) for k in (kps or ["注意边界", "别调过头", "先看结构"]))}]
        for i, (txt, col) in enumerate(zip(texts[:3], colors)):
            box = RoundedRectangle(width=3.5, height=2.4, corner_radius=0.12,
                                   stroke_color=col, fill_opacity=0.12, fill_color=col)
            t = Text(txt, font_size=22, color=WHITE, font=FONT)
            t.width = min(t.width, 3.1)
            g = VGroup(box, t)
            t.move_to(box)
            cards.add(g)
        cards.arrange(RIGHT, buff=0.35).shift(DOWN * 0.2)
        tip = Text("先观察结构稳定性，再追极限参数", font_size=24, color=SECONDARY, font=FONT)
        tip.to_edge(DOWN, buff=0.45)

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(c, shift=UP*0.15) for c in cards], lag_ratio=0.15), run_time=1.6)
        self.play(Indicate(cards[0], color=WARN), run_time=0.8)
        self.play(Write(tip), run_time=1.0)
        self.wait(1.8)
'''
    elif index == 3 or "对比" in title or "差在" in title:
        body = '''
        # Compare columns
        cols = VGroup()
        names = ["方案 A", "方案 B", "方案 C"]
        colors = [WARN, ACCENT, SECONDARY]
        for name, col, kp in zip(names, colors, (kps + ["—", "—", "—"])[:3]):
            box = RoundedRectangle(width=3.4, height=3.6, corner_radius=0.12,
                                   stroke_color=col, fill_opacity=0.1, fill_color=col)
            h = Text(name, font_size=26, color=col, font=FONT)
            b = Text(kp[:30], font_size=20, color=WHITE, font=FONT)
            b.width = min(b.width, 3.0)
            inner = VGroup(h, b).arrange(DOWN, buff=0.4)
            g = VGroup(box, inner)
            inner.move_to(box)
            cols.add(g)
        cols.arrange(RIGHT, buff=0.3).shift(DOWN * 0.15)

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(c) for c in cols], lag_ratio=0.18), run_time=1.8)
        self.play(Indicate(cols[-1], color=SECONDARY), run_time=0.9)
        self.wait(1.8)
'''
    else:
        body = f'''
        # Flow nodes + bullets
        n1 = RoundedRectangle(corner_radius=0.15, width=2.4, height=1.0, color=PRIMARY)
        n2 = RoundedRectangle(corner_radius=0.15, width=2.4, height=1.0, color=SECONDARY)
        n3 = RoundedRectangle(corner_radius=0.15, width=2.4, height=1.0, color=ACCENT)
        t1 = Text("输入", font_size=22, font=FONT, color=PRIMARY)
        t2 = Text("机制", font_size=22, font=FONT, color=SECONDARY)
        t3 = Text("输出", font_size=22, font=FONT, color=ACCENT)
        g1 = VGroup(n1, t1); t1.move_to(n1)
        g2 = VGroup(n2, t2); t2.move_to(n2)
        g3 = VGroup(n3, t3); t3.move_to(n3)
        g1.shift(LEFT * 3.6 + DOWN * 0.2)
        g2.shift(DOWN * 0.2)
        g3.shift(RIGHT * 3.6 + DOWN * 0.2)
        a1 = Arrow(g1.get_right(), g2.get_left(), buff=0.12, color=PRIMARY)
        a2 = Arrow(g2.get_right(), g3.get_left(), buff=0.12, color=SECONDARY)
        bullets = VGroup(
{kp_items}
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).scale(0.88)
        bullets.to_edge(DOWN, buff=0.45)

        self.play(Write(title), run_time=1.1)
        self.play(FadeIn(subtitle), run_time=0.5)
        self.play(FadeIn(g1), run_time=0.5)
        self.play(GrowArrow(a1), FadeIn(g2), run_time=0.9)
        self.play(GrowArrow(a2), FadeIn(g3), run_time=0.9)
        self.play(g2.animate.set_stroke(ACCENT, width=4), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(b, shift=UP*0.1) for b in bullets], lag_ratio=0.12), run_time=1.2)
        self.wait(1.6)
'''

    return f'''
class {cls}(Scene):
    def construct(self):
        self.camera.background_color = BG
        title = Text("{_escape(title[:40])}", font_size=36, color=PRIMARY, font=FONT)
        title.to_edge(UP, buff=0.45)
        subtitle = Text("{_escape(hint[:52])}", font_size=20, color=MUTED, font=FONT)
        subtitle.next_to(title, DOWN, buff=0.25)
{body}
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.45)
'''


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

    scenes_code: list[str] = []
    class_names: list[str] = []
    for i, o in enumerate(outlines, 1):
        title = o.get("title") or f"Scene {i}"
        cls = f"Scene{i}_{_slug(title).replace('-', '_')}"
        cls = re.sub(r"[^0-9A-Za-z_]", "", cls)
        if not cls or not cls[0].isalpha():
            cls = f"Scene{i}"
        class_names.append(cls)
        scenes_code.append(
            _scene_block(
                cls=cls,
                title=str(title),
                hint=_manim_hint(o),
                kps=_clean_kps(o),
                scene_type=str(o.get("type") or "slide"),
                index=i,
            )
        )

    script = f'''"""
Auto-generated tech explainer for: {topic}
Course: {course_title}
Render:
  manim -ql script.py {" ".join(class_names)}
"""
from manim import *

BG = "{PALETTE['BG']}"
PRIMARY = "{PALETTE['PRIMARY']}"
SECONDARY = "{PALETTE['SECONDARY']}"
ACCENT = "{PALETTE['ACCENT']}"
WARN = "{PALETTE['WARN']}"
MUTED = "{PALETTE['MUTED']}"
WHITE = "#E8EEF7"
FONT = "{CJK_FONT}"

{"".join(scenes_code)}
'''
    script_path.write_text(script, encoding="utf-8")
    (out_dir / "concat.txt").write_text(
        "# After manim render, Scene*.mp4 collected under media/\n",
        encoding="utf-8",
    )
    return script_path


def outlines_to_vo_scripts(outlines: list[dict[str, Any]], max_chars: int = 220) -> list[str]:
    """Build beat-friendly VO scripts from outlines (for non-curated topics)."""
    scripts: list[str] = []
    for o in outlines:
        parts: list[str] = []
        title = str(o.get("title") or "").strip()
        if title:
            parts.append(title + "。")
        desc = str(o.get("description") or "").strip()
        # keep first sentence-ish of description
        if desc:
            cut = re.split(r"(?<=[。！？])", desc)
            parts.append("".join(cut[:2]) if cut else desc[:120])
        for kp in o.get("keyPoints") or []:
            s = str(kp).strip()
            if s.startswith("[Manim]"):
                continue
            parts.append(s if s.endswith(("。", "！", "？", ".", "!", "?")) else s + "。")
            if sum(len(p) for p in parts) > max_chars:
                break
        text = re.sub(r"\s+", " ", "".join(parts)).strip()
        if len(text) > max_chars + 40:
            text = text[: max_chars + 39] + "…"
        scripts.append(text or "本节讲解核心概念。")
    return scripts
