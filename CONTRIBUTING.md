# Contributing to TechAnim

## 本地开发

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
make test-import
make lint
```

依赖本机 **OpenMAIC**（默认 `http://127.0.0.1:3000`）做大纲与豆包 TTS。  
Manim / ffmpeg 用于渲染与成片。

## 常用命令

```bash
# 生成（精品主题会自动套 Manim + VO 模板）
python -m pipelines.cli gen "TCP三次握手" --with-manim --compose --beats

# 仅成片
python -m pipelines.cli compose output/<job> --beats --with-manim

# Web
make web   # http://localhost:8765
```

## 新增精品主题模板

1. 在 `templates/manim/` 添加 `*_explainer.py`（6 个 Scene 类）
2. 添加对齐的 `*_vo.json`（字符串数组，顺序=场景序）
3. （可选）添加 `*_storyboard.json`：每场 `{tag,t0,t1}` 时间比例
4. 在 `pipelines/cli.py` 的 `TOPIC_TEMPLATES` 注册关键词（三元组 script, vo, storyboard）

## PR 要求

- 不要提交 `.env`、`output/`、`.venv/`、大视频
- `make lint` 与 `make test-import` 通过
- 若改 compose/TTS，注明是否依赖 OpenMAIC

## CI

见 `docs/ENABLE_CI.md`。需要 `workflow` scope 才能推送 `.github/workflows/ci.yml`。
