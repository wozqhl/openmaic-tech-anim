"""Interactive HTML simulation template catalog for tech explainers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SIM_DIR = ROOT / "templates" / "simulations"
CATALOG_PATH = SIM_DIR / "catalog.json"


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def list_templates() -> list[dict[str, Any]]:
    return list(load_catalog().get("templates") or [])


def _score(text: str, tags: list[str]) -> int:
    t = text.lower()
    score = 0
    for tag in tags:
        tag_l = tag.lower()
        if tag_l in t:
            score += 3
        # loose chinese/english token
        if re.search(re.escape(tag_l), t):
            score += 1
    return score


def match_templates(
    topic: str,
    outlines: list[dict[str, Any]] | None = None,
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Rank templates by topic + outline titles/keyPoints."""
    blob_parts = [topic]
    for o in outlines or []:
        blob_parts.append(str(o.get("title") or ""))
        blob_parts.append(str(o.get("description") or ""))
        for kp in o.get("keyPoints") or []:
            blob_parts.append(str(kp))
    blob = "\n".join(blob_parts)

    ranked: list[tuple[int, dict[str, Any]]] = []
    for tpl in list_templates():
        s = _score(blob, tpl.get("tags") or [])
        # boost if outline type interactive and widget matches
        for o in outlines or []:
            if o.get("type") == "interactive":
                wt = (o.get("widgetType") or "").lower()
                if wt and wt == (tpl.get("widgetType") or "").lower():
                    s += 2
        if s > 0:
            ranked.append((s, tpl))
    ranked.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [t for _, t in ranked[:top_k]]


def copy_matched_templates(
    matches: list[dict[str, Any]],
    dest_dir: Path,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    index: list[dict[str, Any]] = []
    for m in matches:
        src = SIM_DIR / m["file"]
        if not src.exists():
            continue
        dst = dest_dir / m["file"]
        shutil.copy2(src, dst)
        written.append(dst)
        index.append({**m, "path": str(dst.name)})
    (dest_dir / "matched.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # convenience index.html
    links = "\n".join(
        f'<li><a href="{m["file"]}">{m.get("name") or m["id"]}</a> — {m.get("description","")}</li>'
        for m in index
    )
    (dest_dir / "index.html").write_text(
        f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"/><title>仿真模板</title>
<style>body{{font-family:system-ui,sans-serif;background:#0f1419;color:#e8eef7;padding:24px}}
a{{color:#58c4dd}} li{{margin:8px 0}}</style></head>
<body><h1>匹配到的互动仿真</h1><ul>{links}</ul>
<p style="color:#8b9bb4">可在浏览器直接打开各 HTML；也可作为 OpenMAIC interactive 场景参考实现。</p>
</body></html>
""",
        encoding="utf-8",
    )
    return written
