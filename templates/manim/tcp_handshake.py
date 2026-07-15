"""TCP / three-way handshake curated Manim explainer."""

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
        title = Text("没有握手，连接从何而来？", font=FONT, font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.4)
        client = RoundedRectangle(width=2.6, height=1.2, corner_radius=0.12, stroke_color=CYAN)
        server = RoundedRectangle(width=2.6, height=1.2, corner_radius=0.12, stroke_color=GREEN)
        ct = Text("客户端", font=FONT, font_size=24, color=WHITE).move_to(client)
        st = Text("服务端", font=FONT, font_size=24, color=WHITE).move_to(server)
        left = VGroup(client, ct).shift(LEFT * 3.5)
        right = VGroup(server, st).shift(RIGHT * 3.5)
        q = Text("双方如何确认「你能收、我能发」？", font=FONT, font_size=26, color=YELLOW)
        q.to_edge(DOWN, buff=0.5)
        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(left), FadeIn(right), run_time=1.0)
        self.play(Write(q), run_time=1.0)
        self.wait(1.6)


class Scene2_Syn(Scene):
    def construct(self):
        title = Text("第 1 步 · SYN：我想连接", font=FONT, font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.35)
        c = Text("Client", font_size=28, color=CYAN).shift(LEFT * 4 + UP * 0.5)
        s = Text("Server", font_size=28, color=GREEN).shift(RIGHT * 4 + UP * 0.5)
        arrow = Arrow(c.get_right(), s.get_left(), buff=0.3, color=YELLOW, stroke_width=6)
        lab = Text("SYN, seq=x", font_size=26, color=YELLOW).next_to(arrow, UP)
        note = Text("客户端发出同步请求，并带上自己的初始序号", font=FONT, font_size=24, color=MUTED)
        note.to_edge(DOWN, buff=0.45)
        self.play(Write(title), FadeIn(c), FadeIn(s), run_time=1.0)
        self.play(GrowArrow(arrow), FadeIn(lab), run_time=1.2)
        self.play(Write(note), run_time=1.0)
        self.wait(1.6)


class Scene3_SynAck(Scene):
    def construct(self):
        title = Text("第 2 步 · SYN+ACK：我同意，也同步我的序号", font=FONT, font_size=28, color=CYAN)
        title.to_edge(UP, buff=0.35)
        c = Text("Client", font_size=28, color=CYAN).shift(LEFT * 4)
        s = Text("Server", font_size=28, color=GREEN).shift(RIGHT * 4)
        arrow = Arrow(s.get_left(), c.get_right(), buff=0.3, color=GREEN, stroke_width=6)
        lab = Text("SYN+ACK, seq=y, ack=x+1", font_size=24, color=GREEN).next_to(arrow, UP)
        note = Text("服务端确认收到 x，并给出自己的 y", font=FONT, font_size=24, color=MUTED)
        note.to_edge(DOWN, buff=0.45)
        self.play(Write(title), FadeIn(c), FadeIn(s), run_time=1.0)
        self.play(GrowArrow(arrow), FadeIn(lab), run_time=1.3)
        self.play(Write(note), run_time=1.0)
        self.wait(1.6)


class Scene4_Ack(Scene):
    def construct(self):
        title = Text("第 3 步 · ACK：连接建立", font=FONT, font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.35)
        c = Text("Client", font_size=28, color=CYAN).shift(LEFT * 4)
        s = Text("Server", font_size=28, color=GREEN).shift(RIGHT * 4)
        arrow = Arrow(c.get_right(), s.get_left(), buff=0.3, color=CYAN, stroke_width=6)
        lab = Text("ACK, ack=y+1", font_size=26, color=CYAN).next_to(arrow, UP)
        ok = Text("ESTABLISHED：双方都确认了对方的序号空间", font=FONT, font_size=24, color=GREEN)
        ok.to_edge(DOWN, buff=0.45)
        self.play(Write(title), FadeIn(c), FadeIn(s), run_time=1.0)
        self.play(GrowArrow(arrow), FadeIn(lab), run_time=1.2)
        self.play(Write(ok), run_time=1.0)
        self.wait(1.6)


class Scene5_WhyThree(Scene):
    def construct(self):
        title = Text("为什么不是两次？", font=FONT, font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.35)
        a = RoundedRectangle(width=5.2, height=2.8, corner_radius=0.12, stroke_color=RED)
        b = RoundedRectangle(width=5.2, height=2.8, corner_radius=0.12, stroke_color=GREEN)
        at = Text("两次：旧 SYN 重传\n可能让服务端误建连接", font=FONT, font_size=22, color=WHITE)
        bt = Text("三次：客户端最终 ACK\n确认「这是新会话」", font=FONT, font_size=22, color=WHITE)
        ga = VGroup(a, at); at.move_to(a); ga.shift(LEFT * 3.2)
        gb = VGroup(b, bt); bt.move_to(b); gb.shift(RIGHT * 3.2)
        self.play(Write(title), run_time=0.9)
        self.play(FadeIn(ga), FadeIn(gb), run_time=1.2)
        self.play(Indicate(gb, color=GREEN), run_time=1.0)
        self.wait(1.8)


class Scene6_Pitfalls(Scene):
    def construct(self):
        title = Text("工程坑：半连接 · 队列 · 抓包", font=FONT, font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.3)
        items = VGroup(
            Text("SYN 洪水 → 半连接队列被打满", font=FONT, font_size=24, color=YELLOW),
            Text("抓包顺序：SYN → SYN+ACK → ACK", font=FONT, font_size=24, color=WHITE),
            Text("应用层失败 ≠ 握手失败，先看 TCP 状态", font=FONT, font_size=24, color=WHITE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.45).shift(DOWN * 0.1)
        self.play(Write(title), run_time=0.9)
        for it in items:
            self.play(FadeIn(it, shift=RIGHT * 0.15), run_time=0.7)
        self.wait(1.8)
