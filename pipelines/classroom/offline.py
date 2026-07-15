"""Offline outline generator when cloud LLM credits are exhausted."""

from __future__ import annotations

from typing import Any


def offline_outlines(topic: str) -> dict[str, Any]:
    """Deterministic tech-explainer outline pack (4–5 scenes)."""
    t = topic.strip() or "技术主题"
    outlines = [
        {
            "id": "scene_1",
            "type": "slide",
            "title": f"为什么要关心「{t}」",
            "description": f"用工程师日常场景引入 {t}：它解决什么痛点、不理解时会踩哪些坑。",
            "keyPoints": [
                f"{t} 出现在真实系统的哪些位置",
                "常见故障/性能问题往往与其机制有关",
                "本课目标：建立可动画化的结构直觉",
                f"[Manim] 标题浮现后，从真实场景图标拉出指向「{t}」的箭头",
            ],
            "teachingObjective": f"能用一句话说清为什么要学 {t}",
            "estimatedDuration": 90,
            "order": 1,
        },
        {
            "id": "scene_2",
            "type": "interactive",
            "title": f"{t}：核心结构直觉",
            "description": "交互仿真展示主要组件与数据/控制流；用户可逐步推进关键步骤。",
            "keyPoints": [
                "先看结构：角色/组件/边界",
                "可操作：单步播放与重置",
                "aha：抓住那个「少一步就失败」的关键确认",
                "[Manim] 组件方块依次亮起，关键路径脉冲高亮",
            ],
            "teachingObjective": "能画出核心组件关系图",
            "estimatedDuration": 120,
            "order": 2,
            "widgetType": "simulation",
            "widgetOutline": {
                "conceptName": t,
                "task": f"交互演示 {t} 的核心结构与一步步机制",
            },
        },
        {
            "id": "scene_3",
            "type": "interactive",
            "title": "运行机制：时序 / 状态 / 数据流",
            "description": "用时序或状态机动画走读完整路径，并展示异常分支（超时、重试、丢包等）。",
            "keyPoints": [
                "正常路径的状态迁移",
                "可调参数：延迟 / 丢包 / 并发",
                "异常时如何恢复或失败",
                "[Manim] 状态节点按路径点亮，失败边闪红",
            ],
            "teachingObjective": "能口述正常路径与一种失败路径",
            "estimatedDuration": 120,
            "order": 3,
            "widgetType": "simulation",
            "widgetOutline": {
                "conceptName": f"{t} 运行时序",
                "task": "步进展示状态迁移与异常",
            },
        },
        {
            "id": "scene_4",
            "type": "interactive",
            "title": "对比辨析：容易混淆的相近概念",
            "description": "并排对比两种机制，播放差异动画，强化边界条件。",
            "keyPoints": [
                "相同点：解决的问题域",
                "不同点：代价、约束、适用场景",
                "选型口诀：何时用 A，何时用 B",
                "[Manim] 左右分屏，差异行依次高亮",
            ],
            "teachingObjective": "能做一次正确的对比选型",
            "estimatedDuration": 100,
            "order": 4,
            "widgetType": "diagram",
            "widgetOutline": {
                "conceptName": f"{t} 对比",
                "task": "并排对比两种相近机制",
            },
        },
        {
            "id": "scene_5",
            "type": "slide",
            "title": "落地、坑与检查清单",
            "description": f"总结 {t} 的工程落地点、监控指标与常见误解。",
            "keyPoints": [
                "生产中怎么观测它是否健康",
                "Top 3 踩坑与规避",
                "一页检查清单带走",
                f"[Manim] 清单条目打勾动画，收束回 {t} 标题",
            ],
            "teachingObjective": "带走可执行检查清单",
            "estimatedDuration": 90,
            "order": 5,
        },
    ]
    return {
        "courseTitle": t,
        "languageDirective": "全程使用中文授课，术语首次中英对照，口语化适合 TTS。",
        "outlines": outlines,
        "errors": [],
        "eventCount": 0,
        "offline": True,
        "note": "Generated offline because cloud LLM credits were unavailable.",
    }
