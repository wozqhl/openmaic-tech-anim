"""Diffusion model tech explainer — visual-first Manim scenes with beat-aligned VO.

Each Scene class:
- builds a concrete visual metaphor (not bullet lists)
- returns self.vo: short Chinese voiceover matching on-screen beats
"""

from __future__ import annotations

import json
from pathlib import Path

from manim import *

config.background_color = "#0f1419"
BG = "#0f1419"
CYAN = "#58C4DD"
GREEN = "#83C167"
YELLOW = "#FFD93D"
RED = "#FF6B6B"
MUTED = "#8B9BB4"
WHITE = "#E8EEF7"


class Scene1_Hook(Scene):
    """Clear image → noise → denoise. VO matches three beats."""

    def construct(self):
        self.vo = (
            "为什么工程师要关心扩散模型？因为今天的文生图、修图、甚至分子设计，"
            "很多都共用同一套思路：先把数据弄乱成噪声，再学会一步步去噪。"
            "请看：清晰结构被噪声淹没，再反向变清晰。一句话：会去噪，就会生成。"
        )
        title = Text("生成 = 学会去噪", font="PingFang SC", font_size=40, color=CYAN)
        title.to_edge(UP, buff=0.4)

        # "image" as structured grid of squares
        palette = [BLUE_B, BLUE_C, BLUE_D, GREEN_B, GREEN_C, GREEN_D, TEAL, TEAL_C]
        grid = VGroup(*[
            Square(0.28, fill_opacity=0.9, stroke_width=0,
                   fill_color=palette[i % len(palette)])
            for i in range(64)
        ]).arrange_in_grid(8, 8, buff=0.04)
        grid.move_to(ORIGIN)

        noise = VGroup(*[
            Dot(radius=0.06, color=GREY_B)
            for _ in range(180)
        ])
        for d in noise:
            d.move_to([np.random.uniform(-2.2, 2.2), np.random.uniform(-1.8, 1.8), 0])

        caption = Text("前向加噪 → 反向去噪", font="PingFang SC", font_size=26, color=MUTED)
        caption.to_edge(DOWN, buff=0.45)

        self.play(Write(title), run_time=2.10)
        self.play(FadeIn(grid, scale=0.9), run_time=2.10)
        self.wait(1.00)
        self.play(FadeOut(grid), FadeIn(noise), run_time=3.36)
        self.play(Write(caption), run_time=1.68)
        self.wait(0.75)
        clean = VGroup(*[
            Circle(radius=0.15 + 0.12 * (i % 5), stroke_color=CYAN, stroke_width=2)
            for i in range(12)
        ]).arrange_in_grid(3, 4, buff=0.15)
        clean.move_to(ORIGIN)
        self.play(FadeOut(noise), FadeIn(clean), run_time=3.78)
        punch = Text("会去噪，就会生成", font="PingFang SC", font_size=34, color=GREEN)
        punch.next_to(caption, UP, buff=0.25)
        self.play(FadeIn(punch, shift=UP * 0.2), run_time=1.68)
        self.wait(3.00)


class Scene2_Geometry(Scene):
    """Point cloud: data → noise ball → reverse arrows."""

    def construct(self):
        self.vo = (
            "忘掉公式，先看几何。想象一堆数据点，每一步轻轻撒高斯噪声，"
            "形状慢慢糊成各向同性的噪声球。前向过程只负责弄乱数据；"
            "反向过程要学的是：在每个噪声水平下，该把点往哪个方向推回去。"
            "t 越大越像纯噪声，反向走时形状重新长出来——生成就是沿着学好的向量场，从噪声走回数据。"
        )
        title = Text("噪声几何：前向 ↔ 反向", font="PingFang SC", font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.35)

        rng = np.random.default_rng(7)
        n = 80
        # two moons-ish clusters as "data"
        a = rng.normal([-1.1, 0.2], 0.22, size=(n // 2, 2))
        b = rng.normal([1.1, -0.2], 0.22, size=(n // 2, 2))
        data = np.vstack([a, b])

        dots = VGroup(*[Dot(point=[x, y, 0], radius=0.05, color=CYAN) for x, y in data])
        label_data = Text("数据流形", font="PingFang SC", font_size=22, color=MUTED).next_to(dots, DOWN)

        self.play(Write(title), run_time=1.68)
        self.play(FadeIn(dots, lag_ratio=0.01), FadeIn(label_data), run_time=2.52)

        # forward noise
        noisy = data + rng.normal(0, 0.85, size=data.shape)
        noisy_dots = VGroup(*[Dot(point=[x, y, 0], radius=0.05, color=YELLOW) for x, y in noisy])
        label_noise = Text("噪声球 t→T", font="PingFang SC", font_size=22, color=YELLOW).to_edge(DOWN, buff=0.4)
        self.play(
            Transform(dots, noisy_dots),
            FadeOut(label_data),
            FadeIn(label_noise),
            run_time=5.00,
        )
        self.wait(0.75)

        # reverse arrows toward clusters
        arrows = VGroup()
        for x, y in noisy[::4]:
            target = np.array([-1.1, 0.2]) if x < 0 else np.array([1.1, -0.2])
            start = np.array([x, y, 0])
            end = np.array([target[0], target[1], 0])
            v = end - start
            if np.linalg.norm(v) < 0.2:
                continue
            arrows.add(Arrow(start, start + 0.35 * v / np.linalg.norm(v), buff=0,
                             color=GREEN, stroke_width=2, max_tip_length_to_length_ratio=0.25))
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.03), run_time=3.15)

        recovered = VGroup(*[Dot(point=[x, y, 0], radius=0.05, color=GREEN) for x, y in data])
        label_rev = Text("反向：沿向量场走回数据", font="PingFang SC", font_size=22, color=GREEN).to_edge(DOWN, buff=0.4)
        self.play(
            FadeOut(arrows),
            Transform(dots, recovered),
            Transform(label_noise, label_rev),
            run_time=4.62,
        )
        self.wait(2.50)


class Scene3_DenoiseSteps(Scene):
    """Timeline T→0 with residual peeling metaphor."""

    def construct(self):
        self.vo = (
            "运行机制像一条状态机：状态是带噪图像 x 下标 t，动作是预测并减去一点噪声。"
            "网络，常见是 U-Net，每一步估计当前图里噪声长什么样。"
            "调度器决定每步删多少噪声：步数太少会糊，太多浪费算力。"
            "记住：清洁工不是一次擦完，而是从 t 等于 T 走到 t 等于 0，每步只擦一点点。"
        )
        title = Text("去噪时序 t = T → 0", font="PingFang SC", font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=1.68)

        axis = NumberLine(x_range=[0, 10, 1], length=10, color=MUTED)
        axis.shift(DOWN * 2.2)
        t_labels = VGroup(
            Text("t=T 纯噪声", font="PingFang SC", font_size=18, color=YELLOW).next_to(axis.n2p(0), DOWN),
            Text("t=0 清晰", font="PingFang SC", font_size=18, color=GREEN).next_to(axis.n2p(10), DOWN),
        )
        self.play(Create(axis), FadeIn(t_labels), run_time=2.10)

        # canvas blob evolves
        blob = Square(2.4, fill_opacity=0.85, fill_color=GREY_E, stroke_color=YELLOW)
        blob.shift(UP * 0.3)
        tag = Text("x_t", font_size=28, color=WHITE).move_to(blob)
        self.play(FadeIn(blob), FadeIn(tag), run_time=1.68)

        pointer = Triangle(fill_color=CYAN, fill_opacity=1, stroke_width=0).scale(0.15)
        pointer.next_to(axis.n2p(0), UP, buff=0.1)
        self.add(pointer)

        steps = 6
        colors = [GREY_E, GREY_C, GREY_B, BLUE_E, BLUE_C, CYAN]
        for i in range(steps):
            x = 10 * (i + 1) / steps
            new_blob = Square(2.4 - 0.12 * i, fill_opacity=0.9,
                              fill_color=colors[i], stroke_color=GREEN if i == steps - 1 else CYAN)
            new_blob.shift(UP * 0.3)
            residual = Text("− εθ", font_size=26, color=RED).next_to(new_blob, RIGHT)
            self.play(
                pointer.animate.next_to(axis.n2p(x), UP, buff=0.1),
                Transform(blob, new_blob),
                FadeIn(residual, shift=LEFT * 0.2),
                run_time=1.47,
            )
            self.play(FadeOut(residual), run_time=0.53)

        note = Text("每步只去掉一点点预测噪声", font="PingFang SC", font_size=26, color=GREEN)
        note.to_edge(DOWN, buff=0.85)
        self.play(Write(note), run_time=1.89)
        self.wait(2.50)


class Scene4_Compare(Scene):
    """GAN vs VAE vs Diffusion columns."""

    def construct(self):
        self.vo = (
            "和 GAN、VAE 差在哪？GAN 是生成器硬刚判别器，出图快，但训练容易模式崩塌。"
            "VAE 先压缩再解码，训练稳，却容易偏糊。"
            "扩散的训练目标几乎就是回归噪声，监督清晰，质量和多样性往往更好，"
            "代价是推理要跑很多步，所以才有 DDIM 等加速路线。"
            "选型：要质量与稳定，优先扩散；要毫秒级单步，再看 GAN 或蒸馏后的扩散。"
        )
        title = Text("GAN · VAE · Diffusion", font="PingFang SC", font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=1.47)

        def col(name, color, lines, x):
            h = Text(name, font_size=28, color=color)
            body = VGroup(*[Text(s, font="PingFang SC", font_size=20, color=WHITE) for s in lines])
            body.arrange(DOWN, aligned_edge=LEFT, buff=0.18)
            box = RoundedRectangle(width=3.6, height=3.8, corner_radius=0.15,
                                   stroke_color=color, fill_color=BG, fill_opacity=0.5)
            g = VGroup(h, body).arrange(DOWN, buff=0.3)
            g.move_to(box.get_center())
            out = VGroup(box, g)
            out.shift(RIGHT * x + DOWN * 0.15)
            return out

        c1 = col("GAN", RED, ["一次对决出图", "快", "训练不稳 / 易崩"], -4.0)
        c2 = col("VAE", YELLOW, ["编码 → 潜变量 → 解码", "训练稳", "细节易糊"], 0.0)
        c3 = col("Diffusion", GREEN, ["多步可监督去噪", "质量高、多样", "推理步数多"], 4.0)

        for c in (c1, c2, c3):
            self.play(FadeIn(c, shift=UP * 0.15), run_time=1.47)
        pick = Text("要质量稳定 → 扩散　　要极致低延迟 → GAN / 蒸馏", font="PingFang SC",
                    font_size=22, color=MUTED)
        pick.to_edge(DOWN, buff=0.4)
        self.play(Write(pick), run_time=2.10)
        self.play(Indicate(c3[0], color=GREEN), run_time=1.68)
        self.wait(3.00)


class Scene5_Latent(Scene):
    """Pixel space vs latent diffusion pipeline."""

    def construct(self):
        self.vo = (
            "真实落地里，很少在像素上硬扩散。常见链路是：图片先经 VAE 压进潜空间，"
            "在潜空间做扩散去噪，再解码回像素。文本条件通过交叉注意力注入 U-Net。"
            "你听到的 ControlNet、IP-Adapter，本质都是给去噪网络多塞控制信号。"
            "所以工程关键不只是模型结构，还有潜空间对齐、采样步数和引导系数。"
        )
        title = Text("潜空间扩散 · 条件控制", font="PingFang SC", font_size=34, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=1.47)

        nodes = [
            ("像素图", -5.2, MUTED),
            ("VAE 编码", -2.6, YELLOW),
            ("潜空间扩散", 0.2, CYAN),
            ("VAE 解码", 3.0, YELLOW),
            ("输出图", 5.4, GREEN),
        ]
        boxes = VGroup()
        for name, x, col in nodes:
            b = RoundedRectangle(width=2.0, height=1.0, corner_radius=0.12,
                                 stroke_color=col, fill_opacity=0.15, fill_color=col)
            t = Text(name, font="PingFang SC", font_size=22, color=WHITE)
            g = VGroup(b, t)
            t.move_to(b.get_center())
            g.shift(RIGHT * x + UP * 0.5)
            boxes.add(g)

        arrows = VGroup()
        for i in range(len(boxes) - 1):
            arrows.add(Arrow(boxes[i].get_right(), boxes[i + 1].get_left(),
                             buff=0.08, color=MUTED, stroke_width=3))

        cond = Text("文本 / ControlNet 条件 → 注入 U-Net", font="PingFang SC", font_size=24, color=GREEN)
        cond.shift(DOWN * 1.6)

        self.play(LaggedStart(*[FadeIn(b) for b in boxes], lag_ratio=0.15), run_time=2.94)
        self.play(LaggedStart(*[GrowArrow(a) for a in arrows], lag_ratio=0.1), run_time=2.10)
        self.play(Write(cond), run_time=1.89)
        brace = Brace(boxes[2], DOWN, color=CYAN)
        brace_t = Text("在潜空间逐步去噪", font="PingFang SC", font_size=22, color=CYAN)
        brace_t.next_to(brace, DOWN, buff=0.1)
        self.play(GrowFromCenter(brace), FadeIn(brace_t), run_time=1.89)
        self.wait(3.00)


class Scene6_Pitfalls(Scene):
    """Guidance / steps knobs and failure modes."""

    def construct(self):
        self.vo = (
            "踩坑清单：扩散不是一次采样魔法，步数太少会丢结构；"
            "引导系数不是越大越好，过大容易过曝、重复纹理。"
            "还有分布外提示、分辨率乱改、潜空间与 VAE 不匹配，都会让轨迹走歪。"
            "调参时同时看清晰度与结构稳定性，找到边界，而不是把滑条拉满。"
        )
        title = Text("坑与边界：步数 · 引导系数", font="PingFang SC", font_size=32, color=CYAN)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=1.47)

        # two sliders
        def slider(label, y, color):
            line = Line(LEFT * 3.5, RIGHT * 3.5, color=MUTED)
            line.shift(UP * y)
            knob = Dot(line.get_start(), color=color, radius=0.12)
            lab = Text(label, font="PingFang SC", font_size=24, color=color).next_to(line, LEFT, buff=0.3)
            return VGroup(line, knlab := lab, knob), line, knob

        s1, line1, k1 = slider("采样步数", 1.0, YELLOW)
        s2, line2, k2 = slider("引导系数", -0.4, RED)
        self.play(FadeIn(s1), FadeIn(s2), run_time=1.68)

        bad = Text("步数过少 → 糊　|　引导过大 → 过曝 / 纹理崩", font="PingFang SC",
                  font_size=24, color=RED)
        bad.to_edge(DOWN, buff=1.0)
        good = Text("同时观察：清晰度 × 结构稳定性", font="PingFang SC", font_size=26, color=GREEN)
        good.next_to(bad, UP, buff=0.25)

        self.play(k1.animate.move_to(line1.point_from_proportion(0.2)), run_time=2.10)
        self.play(Write(bad), run_time=1.68)
        self.play(k2.animate.move_to(line2.point_from_proportion(0.9)), run_time=2.10)
        self.play(k1.animate.move_to(line1.point_from_proportion(0.65)),
                  k2.animate.move_to(line2.point_from_proportion(0.55)), run_time=2.52)
        self.play(Write(good), run_time=1.68)
        self.wait(3.00)


def export_vo_json(path: Path) -> None:
    scenes = [Scene1_Hook, Scene2_Geometry, Scene3_DenoiseSteps, Scene4_Compare, Scene5_Latent, Scene6_Pitfalls]
    # instantiate without rendering to collect vo — set vo in construct only, so hardcode export
    data = {
        "Scene1_Hook": Scene1_Hook.vo if hasattr(Scene1_Hook, "vo") else None,
    }
    # manual map (construct sets instance attr; export static)
    vos = {
        "Scene1_Hook": (
            "为什么工程师要关心扩散模型？因为今天的文生图、修图、甚至分子设计，"
            "很多都共用同一套思路：先把数据弄乱成噪声，再学会一步步去噪。"
            "请看：清晰结构被噪声淹没，再反向变清晰。一句话：会去噪，就会生成。"
        ),
        "Scene2_Geometry": (
            "忘掉公式，先看几何。想象一堆数据点，每一步轻轻撒高斯噪声，"
            "形状慢慢糊成各向同性的噪声球。前向过程只负责弄乱数据；"
            "反向过程要学的是：在每个噪声水平下，该把点往哪个方向推回去。"
            "t 越大越像纯噪声，反向走时形状重新长出来——生成就是沿着学好的向量场，从噪声走回数据。"
        ),
        "Scene3_DenoiseSteps": (
            "运行机制像一条状态机：状态是带噪图像 x 下标 t，动作是预测并减去一点噪声。"
            "网络，常见是 U-Net，每一步估计当前图里噪声长什么样。"
            "调度器决定每步删多少噪声：步数太少会糊，太多浪费算力。"
            "记住：清洁工不是一次擦完，而是从 t 等于 T 走到 t 等于 0，每步只擦一点点。"
        ),
        "Scene4_Compare": (
            "和 GAN、VAE 差在哪？GAN 是生成器硬刚判别器，出图快，但训练容易模式崩塌。"
            "VAE 先压缩再解码，训练稳，却容易偏糊。"
            "扩散的训练目标几乎就是回归噪声，监督清晰，质量和多样性往往更好，"
            "代价是推理要跑很多步，所以才有 DDIM 等加速路线。"
            "选型：要质量与稳定，优先扩散；要毫秒级单步，再看 GAN 或蒸馏后的扩散。"
        ),
        "Scene5_Latent": (
            "真实落地里，很少在像素上硬扩散。常见链路是：图片先经 VAE 压进潜空间，"
            "在潜空间做扩散去噪，再解码回像素。文本条件通过交叉注意力注入 U-Net。"
            "你听到的 ControlNet、IP-Adapter，本质都是给去噪网络多塞控制信号。"
            "所以工程关键不只是模型结构，还有潜空间对齐、采样步数和引导系数。"
        ),
        "Scene6_Pitfalls": (
            "踩坑清单：扩散不是一次采样魔法，步数太少会丢结构；"
            "引导系数不是越大越好，过大容易过曝、重复纹理。"
            "还有分布外提示、分辨率乱改、潜空间与 VAE 不匹配，都会让轨迹走歪。"
            "调参时同时看清晰度与结构稳定性，找到边界，而不是把滑条拉满。"
        ),
    }
    path.write_text(json.dumps(vos, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    export_vo_json(Path(__file__).with_name("diffusion_vo.json"))
