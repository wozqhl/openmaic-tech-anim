"""HTTP/2 multiplexing curated Manim explainer."""

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
        title = Text("HTTP/1.1 的队头阻塞有多痛？", font=FONT, font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.35)
        boxes = VGroup(*[
            RoundedRectangle(width=1.8, height=0.7, corner_radius=0.08, stroke_color=MUTED)
            for _ in range(4)
        ]).arrange(RIGHT, buff=0.2)
        labels = VGroup(*[Text(f"请求{i}", font=FONT, font_size=18, color=WHITE) for i in range(1, 5)])
        for b, t in zip(boxes, labels):
            t.move_to(b)
        row = VGroup(*[VGroup(b, t) for b, t in zip(boxes, labels)])
        row.arrange(RIGHT, buff=0.2).shift(UP * 0.3)
        block = Text("第一个慢响应堵住后面所有人", font=FONT, font_size=24, color=RED)
        block.to_edge(DOWN, buff=0.5)
        self.play(Write(title), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(r) for r in row], lag_ratio=0.12), run_time=1.2)
        self.play(row[0].animate.set_color(RED), Write(block), run_time=1.2)
        self.wait(1.4)


class Scene2_Streams(Scene):
    def construct(self):
        title = Text("HTTP/2：一条连接，多条流", font=FONT, font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.35)
        pipe = Rectangle(width=10, height=1.2, stroke_color=MUTED)
        pipe.shift(DOWN * 1.5)
        pipe_t = Text("单 TCP 连接", font=FONT, font_size=20, color=MUTED).next_to(pipe, DOWN)
        streams = VGroup()
        colors = [CYAN, GREEN, YELLOW, RED]
        for i, col in enumerate(colors):
            s = Rectangle(width=8, height=0.35, stroke_color=col, fill_opacity=0.25, fill_color=col)
            s.shift(UP * (1.2 - i * 0.55))
            t = Text(f"Stream {i+1}", font_size=18, color=col).move_to(s)
            streams.add(VGroup(s, t))
        self.play(Write(title), run_time=0.9)
        self.play(Create(pipe), FadeIn(pipe_t), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(s, shift=RIGHT * 0.2) for s in streams], lag_ratio=0.12), run_time=1.5)
        self.wait(1.5)


class Scene3_Frames(Scene):
    def construct(self):
        title = Text("帧：流被切成可交错的小块", font=FONT, font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.35)
        frames = VGroup()
        pattern = [CYAN, GREEN, CYAN, YELLOW, GREEN, CYAN, YELLOW, GREEN]
        for i, col in enumerate(pattern):
            f = RoundedRectangle(width=1.0, height=0.9, corner_radius=0.06,
                                 stroke_color=col, fill_opacity=0.3, fill_color=col)
            frames.add(f)
        frames.arrange(RIGHT, buff=0.12).shift(UP * 0.2)
        note = Text("同一连接上交错发送，慢流不再堵死整条管道", font=FONT, font_size=22, color=MUTED)
        note.to_edge(DOWN, buff=0.45)
        self.play(Write(title), run_time=0.9)
        self.play(LaggedStart(*[FadeIn(f, scale=0.8) for f in frames], lag_ratio=0.08), run_time=1.6)
        self.play(Write(note), run_time=1.0)
        self.wait(1.5)


class Scene4_HPACK(Scene):
    def construct(self):
        title = Text("HPACK：头部不再每次整包重传", font=FONT, font_size=30, color=CYAN)
        title.to_edge(UP, buff=0.35)
        big = RoundedRectangle(width=4.5, height=2.5, corner_radius=0.1, stroke_color=RED)
        small = RoundedRectangle(width=2.2, height=1.2, corner_radius=0.1, stroke_color=GREEN)
        bt = Text("HTTP/1 重复头\nUser-Agent…", font=FONT, font_size=20, color=WHITE).move_to(big)
        st = Text("索引 + 差分", font=FONT, font_size=20, color=WHITE).move_to(small)
        left = VGroup(big, bt).shift(LEFT * 3)
        right = VGroup(small, st).shift(RIGHT * 3)
        arrow = Arrow(left.get_right(), right.get_left(), buff=0.2, color=YELLOW)
        self.play(Write(title), run_time=0.9)
        self.play(FadeIn(left), run_time=0.8)
        self.play(GrowArrow(arrow), FadeIn(right), run_time=1.2)
        self.wait(1.5)


class Scene5_ServerPush(Scene):
    def construct(self):
        title = Text("Server Push 与现实取舍", font=FONT, font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.35)
        a = Text("理想：服务端预推 CSS/JS", font=FONT, font_size=24, color=YELLOW)
        b = Text("现实：缓存命中差、复杂度高", font=FONT, font_size=24, color=MUTED)
        c = Text("多数栈更依赖多路复用 + 头部压缩", font=FONT, font_size=24, color=GREEN)
        g = VGroup(a, b, c).arrange(DOWN, aligned_edge=LEFT, buff=0.45)
        self.play(Write(title), run_time=0.9)
        for x in g:
            self.play(FadeIn(x, shift=RIGHT * 0.15), run_time=0.7)
        self.wait(1.6)


class Scene6_Pitfalls(Scene):
    def construct(self):
        title = Text("坑：TCP 层阻塞 · 优先级 · 调试", font=FONT, font_size=30, color=CYAN)
        title.to_edge(UP, buff=0.3)
        items = VGroup(
            Text("多路复用消灭 HTTP 队头阻塞，但不消灭 TCP 丢包阻塞", font=FONT, font_size=22, color=YELLOW),
            Text("流优先级与依赖影响关键资源排程", font=FONT, font_size=22, color=WHITE),
            Text("抓包看 stream id 与 frame type，而不是只看 URL 顺序", font=FONT, font_size=22, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        self.play(Write(title), run_time=0.9)
        for it in items:
            self.play(FadeIn(it), run_time=0.65)
        self.wait(1.6)
