SHELL := /bin/bash
PYTHON ?= python3

QUALITY_PATHS := src tests evaluation/resume_metrics.py
PYTHONPATH_EXPORT := PYTHONPATH=src

.PHONY: install fmt lint typecheck test build run api dev ingest index eval load-test loadtest all docker-build docker-up docker-down stats eval-retrieval eval-grounding stability-60m

install:
	$(PYTHON) -m pip install -U pip
	pip install -r requirements.txt
	pip install -e .

fmt:
	ruff format .

lint:
	ruff check $(QUALITY_PATHS)

typecheck:
	mypy $(QUALITY_PATHS)

test:
	$(PYTHONPATH_EXPORT) pytest --cov=src --cov-report=term-missing --cov-report=xml -q

build:
	$(PYTHON) -m build

run:
	$(PYTHON) -m rag_smart_qa serve

api:
	$(PYTHON) -m rag_smart_qa serve

dev:
	docker compose up --build

ingest:
	$(PYTHON) -m rag_smart_qa ingest

index:
	$(PYTHON) -m rag_smart_qa build-index

eval:
	$(PYTHON) -m rag_smart_qa eval

load-test:
	$(PYTHONPATH_EXPORT) python -m scripts.load_test

loadtest: load-test

stats:
	curl -sS http://127.0.0.1:8000/stats | python3 -m json.tool

eval-retrieval:
	$(PYTHONPATH_EXPORT) python -m scripts.eval_retrieval \
		--eval_jsonl evaluation/datasets/retrieval_eval.jsonl \
		--hybrid_url http://127.0.0.1:8000/retrieve/hybrid \
		--bm25_url http://127.0.0.1:8000/retrieve/bm25 \
		--method POST --payload '{"top_k":5,"rewrite_query":false}' --k 5

eval-grounding:
	$(PYTHONPATH_EXPORT) python -m scripts.grounding_eval export \
		--query_url http://127.0.0.1:8000/query \
		--method POST \
		--payload '{"top_k":12,"rewrite_query":false}' \
		--grounding_queries grounding_queries_100.txt \
		--out_csv grounding_eval_100.csv \
		--concurrency 3 --timeout 60
	$(PYTHONPATH_EXPORT) python -m scripts.grounding_eval score --out_csv grounding_eval_100.csv

stability-60m:
	$(PYTHONPATH_EXPORT) python -m scripts.stability_test \
		--query_url http://127.0.0.1:8000/query \
		--method POST \
		--payload '{"top_k":12,"rewrite_query":false}' \
		--duration_minutes 60 --concurrency 20 \
		--stability_query "How many projects are there in the resume?" \
		--out_csv stability_60m.csv

all:
	$(PYTHONPATH_EXPORT) python -m scripts.run_all

docker-build:
	docker build -t rag-smart-qa:latest .

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v
