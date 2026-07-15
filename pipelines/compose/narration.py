"""Build narration markdown from outlines for TTS / voiceover."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_narration(
    *,
    course_title: str,
    outlines: list[dict[str, Any]],
    path: Path,
    language_directive: str = "",
) -> Path:
    lines = [
        f"# 旁白稿 · {course_title}",
        "",
    ]
    if language_directive:
        lines += [f"> 语言指令：{language_directive}", ""]

    for i, o in enumerate(outlines, 1):
        title = o.get("title") or f"场景{i}"
        lines.append(f"## 场景 {i} · {title}")
        lines.append("")
        obj = o.get("teachingObjective") or ""
        if obj:
            lines.append(f"**教学目标：** {obj}")
            lines.append("")
        lines.append("**口播：**")
        lines.append("")
        # Spoken style from description + key points
        desc = o.get("description") or ""
        if desc:
            lines.append(desc)
            lines.append("")
        for kp in o.get("keyPoints") or []:
            if isinstance(kp, str) and kp.startswith("[Manim]"):
                continue
            lines.append(f"- {kp}")
        lines.append("")
        lines.append(f"*（建议时长约 {o.get('estimatedDuration', 120)} 秒）*")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
