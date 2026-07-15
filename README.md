# TechAnim · 技术科普动画工坊

基于 **OpenMAIC**（多智能体互动课堂）+ **Manim**（3Blue1Brown 风格动画）的技术科普动画生成系统。

目标：输入一个技术主题（如「TCP 三次握手」「Transformer Attention」），输出：

1. **互动课堂**（OpenMAIC）— 幻灯片 + 交互仿真 HTML + AI 老师讲解/TTS  
2. **电影级动画脚本**（Manim）— 可渲染为讲解视频  
3. **分镜与旁白稿** — 可直接用于剪辑 / 配音

## 架构

```
主题 / PDF
   │
   ▼
┌──────────────────┐
│  Planner         │  拆分「概念→机制→对比→应用→误区」
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
 OpenMAIC   Manim
 课堂生成   动画脚本
 (互动仿真)  (几何/流程/时序)
    │         │
    └────┬────┘
         ▼
   Compose / Export
   (旁白、字幕、成片清单)
```

## 两种输出形态

| 形态 | 引擎 | 适合 | 特点 |
|------|------|------|------|
| 互动课堂 | OpenMAIC | 边学边点、仿真实验 | 多智能体、白板、豆包 TTS、HTML 仿真 |
| 科普动画 | Manim | B 站/短视频技术详解 | 几何直觉、时序动画、电影级节奏 |

## 快速开始

### 前置

- OpenMAIC 已在本机运行：`http://localhost:3000`（见 `~/OpenMAIC`）
- Python 3.10+ 推荐；可选 `manim` / `ffmpeg` 用于视频渲染

```bash
cd ~/openmaic-tech-anim
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 复制环境
cp .env.example .env
# 编辑 OPENMAIC_BASE_URL / 模型等

# 生成「分镜 + OpenMAIC 大纲 + Manim 脚本」
python -m pipelines.cli gen "TCP三次握手" --style tech-explainer

# 仅规划（不调 API）
python -m pipelines.cli plan "Transformer Attention"

# 渲染 Manim 草稿（需安装 manim）
python -m pipelines.cli render output/<job_id>/manim/script.py --ql
```

## 目录

```
openmaic-tech-anim/
  pipelines/
    classroom/     # OpenMAIC API 客户端 + 技术科普 prompt 包装
    manim/         # Manim 脚本生成与渲染
    compose/       # 成片清单、旁白、导出
    cli.py         # 统一入口
  templates/
    prompts/       # 技术科普专用提示词
  examples/        # 示例主题
  output/          # 生成产物
  scripts/         # 运维辅助
```

## 与 OpenMAIC 的关系

- **不 fork** 上游：作为上层应用调用本机 OpenMAIC HTTP API  
- 互动仿真场景强制引导 `type=interactive` + `widgetType=simulation`  
- TTS 复用 OpenMAIC 已配置的 **豆包 TTS** / 代理  
- 模型默认 `grok:grok-4.5`（与 OpenMAIC `.env.local` 一致）

## 互动仿真模板（P2）

目录：`templates/simulations/`

| ID | 名称 | 适合主题 |
|----|------|----------|
| `protocol-handshake` | 协议握手时序 | TCP/TLS 握手 |
| `state-machine` | 状态机步进 | 连接生命周期、调度 |
| `data-flow` | 数据流管道 | 流水线、Attention、ETL |
| `hash-chain` | 哈希链式区块 | 区块链、Git |
| `compare-two` | 并排对比 | HTTP/1 vs HTTP/2 等 |

```bash
# 列出模板
python -m pipelines.cli sims

# 按主题匹配
python -m pipelines.cli sims "TCP三次握手"

# gen 时自动复制匹配模板到 output/.../simulations/
python -m pipelines.cli gen "区块链哈希链"
open output/.../simulations/index.html
```

## 分阶段交付

| 阶段 | 内容 | 状态 |
|------|------|------|
| P1 | 项目骨架、CLI、OpenMAIC 大纲对接、Manim 脚本生成、示例主题 | ✅ |
| P2 | 互动仿真 HTML 模板库（时序图/状态机/数据流/哈希链/对比） | ✅ |
| P3 | 豆包 TTS + ffmpeg 成片（slide/manim 轨） | ✅ |
| P3b | 完整 Manim CE 渲染（可选，需 cairo/manim） | 部分 — 脚本已生成，本机 manim 未装齐 |
| P4 | Web UI / 微信触发「科普一下 XXX」 | 待确认 |

## License

MIT（本仓库编排层）；OpenMAIC / Manim 遵循各自许可证。


## 成片（P3）

```bash
# 1) 生成大纲/旁白/仿真
python -m pipelines.cli gen "你的技术主题"

# 2) 豆包 TTS + 幻灯视频合成 final.mp4
python -m pipelines.cli compose output/<job_dir>           # 全部场景
python -m pipelines.cli compose output/<job_dir> --max-scenes 2   # 快速试片

# 播放
open output/<job_dir>/video/final.mp4
```

成片管线：大纲 → OpenMAIC 豆包 TTS（`/api/generate/tts`）→ ffmpeg 中文幻灯片轨 → 音画合成 → concat。
若日后安装 Manim，同一 `compose` 会优先使用 `manim/**/*.mp4` 作为画面轨。


## Web 入口（P4）

```bash
cd ~/openmaic-tech-anim
bash scripts/start-web.sh
# 打开 http://localhost:8765
```

API：
- `POST /api/jobs` `{ "topic": "TCP三次握手", "compose": true, "max_scenes": 3 }`
- `POST /api/chat` `{ "text": "科普一下 Transformer Attention" }`
- `GET /api/jobs/{id}` 进度
- `GET /api/jobs/{id}/video` 下载 final.mp4

短语：`科普一下 …` / `状态` / `review`


## 运维小工具

```bash
# xAI API Key 额度不足时：从 Hermes OAuth 同步可用 token 并重启 OpenMAIC
python3 scripts/sync-xai-oauth-to-openmaic.py --restart

# 一键：生成 + 成片
python -m pipelines.cli gen "DNS解析" --compose --with-manim
# 仅对已有 job 渲染 Manim 并成片
python -m pipelines.cli compose output/<job> --with-manim
```


## 成片质量优化（持续）

```bash
# 推荐：分句 TTS + 字幕烧录 + 智能慢放对齐（非循环）
python -m pipelines.cli compose output/<job> \
  --vo-json output/<job>/manim/diffusion_vo.json \
  --beats

# 已知主题会自动套用精品 Manim 模板（如 diffusion / 扩散）
python -m pipelines.cli gen "Diffusion model" --compose --with-manim --beats
```

对齐策略：
1. 旁白按句切分 → 逐句豆包 TTS → 合并并生成 SRT
2. Manim 画面优先 **慢放到匹配音长**（上限 1.55×），不足再定格尾帧
3. 烧录中文字幕；统一 1280×720 重编码
