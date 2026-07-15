# PR 检查清单（维护者可勾选）
## 变更类型
- [ ] Bug fix
- [ ] Feature
- [ ] Docs / 模板
- [ ] 重构 / CI

## 自检
- [ ] 未提交 `.env` / 密钥 / `output/` 大文件
- [ ] 本地 `python -m pipelines.cli -h` 可运行
- [ ] 若改 compose/TTS：说明是否需要 OpenMAIC
- [ ] 若新增 Manim 模板：附主题关键词与 VO json

## 测试
- [ ] CI 通过
- [ ] （可选）端到端 gen/compose 截图或路径说明
