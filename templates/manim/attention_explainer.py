"""Transformer / Self-Attention tech explainer — visual Manim scenes + beat VO."""

from manim import *

config.background_color = "#0f1419"
CYAN = "#58C4DD"
GREEN = "#83C167"
YELLOW = "#FFD93D"
RED = "#FF6B6B"
MUTED = "#8B9BB4"
WHITE = "#E8EEF7"
PURPLE = "#C792EA"


class Scene1_Hook(Scene):
    def construct(self):
        title = Text("Attention is All You Need", font="PingFang SC", font_size=36, color=CYAN)
        title.to_edge(UP, buff=0.35)
        sub = Text("先忘掉公式：句子里的词如何互相「点名」", font="PingFang SC", font_size=24, color=MUTED)
        sub.next_to(title, DOWN, buff=0.25)

        words = ["机器", "学习", "很", "有趣"]
        boxes = VGroup()
        for w in words:
            b = RoundedRectangle(width=1.6, height=0.7, corner_radius=0.1,
                                 stroke_color=CYAN, fill_opacity=0.15, fill_color=CYAN)
            t = Text(w, font="PingFang SC", font_size=26, color=WHITE)
            g = VGroup(b, t)
            t.move_to(b)
            boxes.add(g)
        boxes.arrange(RIGHT, buff=0.35).shift(DOWN * 0.2)

        self.play(Write(title), FadeIn(sub), run_time=1.4)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.2) for b in boxes], lag_ratio=0.12), run_time=1.6)

        # "有趣" attends to "学习"
        arrow = Arrow(boxes[3].get_top(), boxes[1].get_top() + UP * 0.1,
                      buff=0.1, color=YELLOW, stroke_width=4)
        note = Text("「有趣」在问：我该多看谁？", font="PingFang SC", font_size=24, color=YELLOW)
        note.to_edge(DOWN, buff=0.5)
        self.play(GrowArrow(arrow), Write(note), run_time=1.6)
        self.play(Indicate(boxes[1], color=GREEN), run_time=1.2)
        punch = Text("注意力 = 动态加权的上下文读取", font="PingFang SC", font_size=28, color=GREEN)
        punch.next_to(note, UP, buff=0.2)
        self.play(FadeIn(punch), run_time=1.0)
        self.wait(2.0)


class Scene2_QKV(Scene):
    def construct(self):
        title = Text("Q · K · V 三件套", font="PingFang SC", font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=1.0)

        def card(name, desc, color, x):
            box = RoundedRectangle(width=3.2, height=3.2, corner_radius=0.15,
                                   stroke_color=color, fill_opacity=0.12, fill_color=color)
            n = Text(name, font_size=40, color=color)
            d = Text(desc, font="PingFang SC", font_size=22, color=WHITE)
            g = VGroup(n, d).arrange(DOWN, buff=0.35)
            out = VGroup(box, g)
            g.move_to(box)
            out.shift(RIGHT * x)
            return out

        q = card("Q", "我在找什么\nQuery", YELLOW, -4)
        k = card("K", "我有什么标签\nKey", CYAN, 0)
        v = card("V", "我携带的内容\nValue", GREEN, 4)

        for c in (q, k, v):
            self.play(FadeIn(c, shift=UP * 0.15), run_time=0.9)
        formula = Text("score = Q · Kᵀ   →   softmax   →   加权 V", font_size=26, color=MUTED)
        formula.to_edge(DOWN, buff=0.45)
        self.play(Write(formula), run_time=1.4)
        self.wait(2.2)


class Scene3_Matrix(Scene):
    def construct(self):
        title = Text("注意力矩阵：谁看谁", font="PingFang SC", font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.25)
        self.play(Write(title), run_time=0.9)

        n = 4
        labels = ["W1", "W2", "W3", "W4"]
        grid = VGroup()
        cells = []
        for i in range(n):
            row = VGroup()
            for j in range(n):
                # diagonal + near stronger
                strength = 0.9 if i == j else (0.55 if abs(i - j) == 1 else 0.2)
                # discrete palette by strength
                col = CYAN if strength > 0.7 else (BLUE_D if strength > 0.4 else GREY_E)
                sq = Square(0.7, fill_opacity=0.95, stroke_width=1, stroke_color=MUTED, fill_color=col)
                row.add(sq)
                cells.append((sq, strength, i, j))
            row.arrange(RIGHT, buff=0.08)
            grid.add(row)
        grid.arrange(DOWN, buff=0.08)
        grid.move_to(ORIGIN)

        left = VGroup(*[Text(l, font_size=20, color=MUTED) for l in labels]).arrange(DOWN, buff=0.42)
        left.next_to(grid, LEFT, buff=0.25)
        top = VGroup(*[Text(l, font_size=20, color=MUTED) for l in labels]).arrange(RIGHT, buff=0.42)
        top.next_to(grid, UP, buff=0.2)

        self.play(FadeIn(grid), FadeIn(left), FadeIn(top), run_time=1.4)
        # highlight one query row
        self.play(*[cells[j][0].animate.set_stroke(YELLOW, 3) for j in range(n)], run_time=1.0)
        note = Text("每一行：某个词对所有位置的注意力分布", font="PingFang SC", font_size=24, color=YELLOW)
        note.to_edge(DOWN, buff=0.4)
        self.play(Write(note), run_time=1.2)
        self.wait(2.0)


class Scene4_MultiHead(Scene):
    def construct(self):
        title = Text("多头注意力：多视角并行", font="PingFang SC", font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.9)

        heads = VGroup()
        colors = [YELLOW, CYAN, GREEN, PURPLE]
        names = ["语法", "指代", "位置", "语义"]
        for name, col in zip(names, colors):
            c = Circle(radius=0.7, stroke_color=col, fill_opacity=0.15, fill_color=col)
            t = Text(name, font="PingFang SC", font_size=22, color=WHITE)
            heads.add(VGroup(c, t))
        heads.arrange(RIGHT, buff=0.5).shift(UP * 0.4)
        for h in heads:
            h[1].move_to(h[0])

        self.play(LaggedStart(*[FadeIn(h, scale=0.8) for h in heads], lag_ratio=0.15), run_time=1.6)
        merge = Text("拼接 → 线性投影 → 综合上下文", font="PingFang SC", font_size=26, color=GREEN)
        merge.to_edge(DOWN, buff=0.6)
        arrows = VGroup(*[
            Arrow(h.get_bottom(), merge.get_top() + UP * 0.3 + RIGHT * (i - 1.5) * 0.2,
                  buff=0.1, color=MUTED, stroke_width=2)
            for i, h in enumerate(heads)
        ])
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.08), run_time=1.2)
        self.play(Write(merge), run_time=1.0)
        self.wait(2.0)


class Scene5_Stack(Scene):
    def construct(self):
        title = Text("Transformer 层叠：编码 / 解码直觉", font="PingFang SC", font_size=30, color=CYAN)
        title.to_edge(UP, buff=0.25)
        self.play(Write(title), run_time=0.9)

        def block(label, color, y):
            b = RoundedRectangle(width=5.5, height=0.85, corner_radius=0.1,
                                 stroke_color=color, fill_opacity=0.12, fill_color=color)
            t = Text(label, font="PingFang SC", font_size=22, color=WHITE)
            g = VGroup(b, t)
            t.move_to(b)
            g.shift(UP * y)
            return g

        layers = VGroup(
            block("输入嵌入 + 位置编码", MUTED, 1.8),
            block("Multi-Head Self-Attention", CYAN, 0.7),
            block("前馈网络 FFN", GREEN, -0.4),
            block("残差 + LayerNorm（每层都有）", YELLOW, -1.5),
        )
        for L in layers:
            self.play(FadeIn(L, shift=RIGHT * 0.2), run_time=0.7)
        note = Text("堆很多层 = 反复「读上下文 → 变换特征」", font="PingFang SC", font_size=24, color=MUTED)
        note.to_edge(DOWN, buff=0.35)
        self.play(Write(note), run_time=1.0)
        self.wait(2.0)


class Scene6_Pitfalls(Scene):
    def construct(self):
        title = Text("工程坑：长度 · 算力 · 位置", font="PingFang SC", font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.8)

        items = [
            ("二次复杂度", "序列长度 L → 注意力约 O(L²)，长文贵"),
            ("位置编码", "没有位置信息，词袋会乱；RoPE / ALiBi 是常见解"),
            ("KV Cache", "推理时缓存 K/V，避免每步重算历史"),
        ]
        blocks = VGroup()
        for h, d in items:
            head = Text(h, font="PingFang SC", font_size=26, color=YELLOW)
            body = Text(d, font="PingFang SC", font_size=22, color=WHITE)
            blocks.add(VGroup(head, body).arrange(DOWN, aligned_edge=LEFT, buff=0.12))
        blocks.arrange(DOWN, aligned_edge=LEFT, buff=0.45).shift(LEFT * 0.2 + DOWN * 0.1)
        for b in blocks:
            self.play(FadeIn(b, shift=UP * 0.1), run_time=0.9)
        tip = Text("选型：短序列全注意力；超长文考虑稀疏 / 线性注意力", font="PingFang SC",
                 font_size=22, color=GREEN)
        tip.to_edge(DOWN, buff=0.35)
        self.play(Write(tip), run_time=1.0)
        self.wait(2.2)
