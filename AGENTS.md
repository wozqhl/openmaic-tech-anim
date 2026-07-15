# TechAnim 项目规则

## 目标
技术科普动画：OpenMAIC 互动课堂 + Manim 详解动画。

## 执行偏好
- 用户说「你来操作 / 必须你来做」时直接用工具执行
- 资金/外部副作用无关；API 调用走本机 OpenMAIC，默认 dry 校验连通性
- 分阶段 + 确认后再进入下一阶段

## 容器
优先 Apple container：https://github.com/apple/container

## OpenMAIC 依赖
- 默认 `OPENMAIC_BASE_URL=http://127.0.0.1:3000`
- 生成前 `curl /api/health` + `/api/verify-model`
- Node 访问 xAI 需 Clash `:7890` + `NODE_USE_ENV_PROXY=1`（见 `~/OpenMAIC/.env.local`）

## 产出约定
- 每次 `gen` 在 `output/<timestamp>_<slug>/` 写：
  - `plan.md` 叙事弧
  - `classroom/outlines.json` OpenMAIC 大纲
  - `manim/script.py` 可渲染脚本
  - `narration.md` 旁白稿
