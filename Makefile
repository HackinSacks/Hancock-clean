.PHONY: install install-train venv test server dataset finetune-debug ollama-pull

venv:
	python3 -m venv .venv
	.venv/bin/pip install -U pip

install: venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

install-train: install
	.venv/bin/pip install -r requirements-train.txt

test:
	.venv/bin/pytest -q

server:
	.venv/bin/python -m hancock --server

dataset:
	.venv/bin/python -m training.pipeline

finetune-debug:
	.venv/bin/python -m training.finetune_tiny_debug

ollama-pull:
	ollama pull llama3.1:8b || ollama pull mistral:7b
