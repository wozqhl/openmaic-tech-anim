# TechAnim developer shortcuts
.PHONY: help install web stack lint test-import gen-tcp compose-last push

help:
	@echo "make install     - venv deps"
	@echo "make web         - start Web UI :8765"
	@echo "make stack       - start OpenMAIC helpers + web (if scripts present)"
	@echo "make lint        - ruff"
	@echo "make test-import - import smoke"
	@echo "make gen-tcp     - sample gen TCP (needs OpenMAIC)"
	@echo "make compose-last ARGS='--beats' - compose newest output job"

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install ruff

web:
	bash scripts/start-web.sh

stack:
	bash scripts/start-stack.sh

lint:
	.venv/bin/ruff check pipelines web scripts --select E,F,W --ignore E501,E402

test-import:
	.venv/bin/python -c "from pipelines.compose.beats import split_beats; assert len(split_beats('第一句足够长的旁白文本内容。第二句也足够长不会被合并。'))>=2"
	.venv/bin/python -c "from pipelines.manim.generator import generate_manim_project, outlines_to_vo_scripts"
	.venv/bin/python -m pipelines.cli -h >/dev/null

gen-tcp:
	.venv/bin/python -m pipelines.cli gen "TCP三次握手" --with-manim --compose --beats

compose-last:
	@job=$$(ls -td output/*/ 2>/dev/null | head -1); \
	if [ -z "$$job" ]; then echo "no output job"; exit 1; fi; \
	echo "compose $$job $(ARGS)"; \
	.venv/bin/python -m pipelines.cli compose "$$job" $(ARGS)
