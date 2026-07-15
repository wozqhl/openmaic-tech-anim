"""KV Cache & long-context decoding curated Manim explainer."""

from manim import *

config.background_color = "#0f1419"
CYAN = "#58C4DD"
GREEN = "#83C167"
YELLOW = "#FFD93D"
RED = "#FF6B6B"
MUTED = "#8B9BB4"
WHITE = "#E8EEF7"
FONT = "PingFang SC"


class Scene1_Hook(Scene):
    def construct(self):
        title = Text("自回归解码：每一步都要回头看历史", font=FONT, font_size=30, color=CYAN)
        title.to_edge(UP, buff=0.35)
        toks = VGroup(*[
            RoundedRectangle(width=0.9, height=0.7, corner_radius=0.08, stroke_color=CYAN)
            for _ in range(6)
        ]).arrange(RIGHT, buff=0.12)
        for i, b in enumerate(toks):
            t = Text(str(i + 1), font_size=18, color=WHITE).move_to(b)
            toks[i] = VGroup(b, t)
        toks.arrange(RIGHT, buff=0.12).shift(UP * 0.2)
        note = Text("若每步重算全部历史 K/V，成本随长度爆炸", font=FONT, font_size=22, color=YELLOW)
        note.to_edge(DOWN, buff=0.45)
        self.play(Write(title), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(t) for t in toks], lag_ratio=0.1), run_time=1.3)
        self.play(Write(note), run_time=1.0)
        self.wait(1.4)


class Scene2_WhatIsKV(Scene):
    def construct(self):
        title = Text("K 与 V：注意力里可缓存的历史表示", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.35)
        k = RoundedRectangle(width=3.5, height=2.2, corner_radius=0.12, stroke_color=YELLOW)
        v = RoundedRectangle(width=3.5, height=2.2, corner_radius=0.12, stroke_color=GREEN)
        kt = Text("Key\n我是谁/可被匹配", font=FONT, font_size=22, color=WHITE).move_to(k)
        vt = Text("Value\n匹配后取走的内容", font=FONT, font_size=22, color=WHITE).move_to(v)
        left = VGroup(k, kt).shift(LEFT * 3)
        right = VGroup(v, vt).shift(RIGHT * 3)
        self.play(Write(title), run_time=0.9)
        self.play(FadeIn(left), FadeIn(right), run_time=1.2)
        self.wait(1.5)


class Scene3_CacheHit(Scene):
    def construct(self):
        title = Text("KV Cache：历史算一次，后面只增量追加", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.3)
        cache = RoundedRectangle(width=8.5, height=2.0, corner_radius=0.12, stroke_color=CYAN)
        cache.shift(UP * 0.3)
        old = Text("已缓存的历史 token 的 K/V", font=FONT, font_size=22, color=MUTED).move_to(cache)
        plus = Text("+ 本步新 token 的 K/V", font=FONT, font_size=24, color=GREEN)
        plus.next_to(cache, DOWN, buff=0.45)
        self.play(Write(title), run_time=0.9)
        self.play(FadeIn(cache), FadeIn(old), run_time=1.0)
        self.play(Write(plus), run_time=1.0)
        self.wait(1.5)


class Scene4_Complexity(Scene):
    def construct(self):
        title = Text("复杂度直觉：时间省下了，显存涨上去了", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.35)
        a = Text("无缓存：每步扫全历史 → 算力随步数平方级难受", font=FONT, font_size=22, color=RED)
        b = Text("有缓存：每步 O(新 token) 注意力增量", font=FONT, font_size=22, color=GREEN)
        c = Text("代价：K/V 占用显存 ∝ 层数 × 头数 × 序列长", font=FONT, font_size=22, color=YELLOW)
        g = VGroup(a, b, c).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        self.play(Write(title), run_time=0.9)
        for x in g:
            self.play(FadeIn(x), run_time=0.7)
        self.wait(1.5)


class Scene5_Paged(Scene):
    def construct(self):
        title = Text("工程演进：Paging / 量化 / 前缀复用", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.35)
        cards = VGroup()
        for name, col in [("PagedAttention", CYAN), ("KV 量化", YELLOW), ("Prefix Cache", GREEN)]:
            box = RoundedRectangle(width=3.3, height=2.0, corner_radius=0.1,
                                   stroke_color=col, fill_opacity=0.12, fill_color=col)
            t = Text(name, font=FONT, font_size=22, color=WHITE).move_to(box)
            cards.add(VGroup(box, t))
        cards.arrange(RIGHT, buff=0.3).shift(DOWN * 0.1)
        self.play(Write(title), run_time=0.9)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.1) for c in cards], lag_ratio=0.15), run_time=1.5)
        self.wait(1.5)


class Scene6_Pitfalls(Scene):
    def construct(self):
        title = Text("坑：显存打满 · 错误复用 · 并发调度", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.3)
        items = VGroup(
            Text("长上下文对话先爆的是 KV，不是参数本身", font=FONT, font_size=22, color=YELLOW),
            Text("前缀缓存 key 不一致会导致错答", font=FONT, font_size=22, color=WHITE),
            Text("连续批处理要在吞吐与延迟间权衡", font=FONT, font_size=22, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        self.play(Write(title), run_time=0.9)
        for it in items:
            self.play(FadeIn(it), run_time=0.65)
        self.wait(1.6)
