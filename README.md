# rag-smart-qa

Config-driven FastAPI RAG system with strict grounding, hybrid retrieval (BM25 + dense), reproducible evaluation, and a full Next.js knowledge workspace for uploads, chat, citations, summaries, and document management.

## Core guarantees
- Answers must be grounded in retrieved evidence.
- Citation validation is enforced.
- If evidence quality is weak, system refuses: `Not available in the provided documents.`
- Metrics are exposed via Prometheus and evaluation scripts.

## Application architecture
- `src/api/routes/`: modular FastAPI routers for uploads, documents, chat, summaries, health, settings, and legacy query endpoints.
- `src/services/`: document lifecycle, SQLite metadata persistence, summary generation, storage abstraction, and chat session orchestration.
- `web/`: Next.js 14 App Router frontend with Tailwind, React Query, dashboard, chat, knowledge base, summaries, and settings pages.
- `data/raw/documents/uploads/`: local-first file storage abstraction ready to be swapped for object storage later.
- `data/processed/metadata/app.db`: SQLite metadata for documents, chat sessions/messages, citations, and cached summaries.

## API endpoints
- `GET /healthz`
- `GET /health`
- `POST /query`
- `GET /metrics`
- `GET /stats` (docs/chunks/vectors + active index paths)
- `POST /retrieve/bm25` (baseline sparse retrieval)
- `POST /retrieve/hybrid` (hybrid retrieval only)
- `POST /debug/retrieval` (stage-wise scores/counts; enable via config/env)
- `POST /api/upload`
- `GET /api/documents`
- `GET /api/documents/{id}`
- `DELETE /api/documents/{id}`
- `POST /api/documents/{id}/reindex`
- `GET /api/documents/{id}/summary`
- `POST /api/chat/query`
- `GET /api/chat/sessions`
- `GET /api/chat/sessions/{id}`
- `DELETE /api/chat/sessions/{id}`
- `GET /api/citations/{citation_id}`
- `GET /api/settings`
- `GET /readiness`

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Build index and run API
```bash
source .venv/bin/activate
PYTHONPATH=src python -m scripts.ingest_data
PYTHONPATH=src python -m scripts.build_index --config configs/dev.yaml
PYTHONPATH=src python -m scripts.run_api
```

Open Swagger: `http://127.0.0.1:8000/docs`

## Run the full web app
```bash
cp .env.example .env
cp web/.env.example web/.env.local

make api
# in another terminal
make web
```

Frontend: `http://127.0.0.1:3000`

## Docker compose
```bash
docker compose up --build
```

This starts:
- FastAPI API on `http://127.0.0.1:8000`
- Next.js web app on `http://127.0.0.1:3000`

## Upload, indexing, and citations flow
1. Files are uploaded through `POST /api/upload` and stored locally under `data/raw/documents/uploads/<user>/`.
2. Document metadata is persisted to SQLite immediately with `queued` indexing state.
3. A background rebuild regenerates chunks, BM25, vector embeddings, and per-document summary cache.
4. Chat responses persist the session, assistant message, and citation records.
5. Clicking a citation in the web app opens the cited excerpt and links back to the document detail page.

## Auth and storage notes
- Auth is feature-flagged in backend settings and intentionally abstracted behind `AuthService`.
- In single-user mode the app uses `local-user`; when auth is enabled, pass the configured user header until a Clerk/Firebase adapter is wired.
- File storage is local-first through `StorageService`; the API surface is ready for a future S3/GCS implementation.

## Known limitations
- PDF source highlighting is excerpt-based today; the document viewer focuses on cited chunk text and page number instead of byte-perfect PDF offsets.
- Upload indexing currently rebuilds the canonical corpus to keep BM25 and FAISS/Chroma consistent across providers.
- Frontend build/test commands require Node.js and npm to be installed locally.

## Quick verification
```bash
curl -sS http://127.0.0.1:8000/healthz | python3 -m json.tool
curl -sS -X POST "http://127.0.0.1:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"How many projects are there in the resume?","top_k":8,"rewrite_query":false}' \
  | python3 -m json.tool
```

## Debug retrieval path
Enable one of:
- Config: `api.enable_debug_retrieval_endpoint: true`
- Env: `RAG_DEBUG_RETRIEVAL=1`

Then:
```bash
curl -sS -X POST "http://127.0.0.1:8000/debug/retrieval" \
  -H "Content-Type: application/json" \
  -d '{"query":"How many projects are there in the resume?","top_k":8,"rewrite_query":false}' \
  | python3 -m json.tool
```

Returned debug includes stage counts/scores:
- `dense_hits`, `bm25_hits`, `fusion_hits`, `rerank_hits`, `final_hits`
- `threshold_applied`
- `top_scores` per stage

## Reproducible resume metrics

Generate all machine-readable artifacts under `experiments/metrics/`:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m scripts.measure_resume_metrics
```

This script produces:
- `experiments/metrics/dataset_stats.json`
- `experiments/metrics/latency_dense.json`
- `experiments/metrics/latency_hybrid.json`
- `experiments/metrics/retrieval_comparison.json`
- `experiments/metrics/hallucination_report.json`
- `experiments/metrics/load_test_report.json`
- `experiments/metrics/resume_metrics.json`
- `experiments/metrics/resume_bullets.md`

What is measured:
- Dataset size from `data/processed/chunks/chunks.jsonl` and the persisted index directories.
- Dense-only vs hybrid retrieval latency on the fixed query set in `evaluation/datasets/resume_retrieval_eval.jsonl`.
- Precision@1/3/5/10, Recall@1/3/5/10, MRR, and hit rate@k for dense-only vs hybrid retrieval.
- Offline hallucination rate from the gold file `evaluation/datasets/resume_hallucination_eval.jsonl`.
- Real HTTP load-test results against a local `uvicorn` process.

What is offline vs online:
- Offline and reproducible without API keys: dataset stats, retrieval latency, retrieval quality, and the fallback-answer hallucination evaluation.
- Online only when valid model credentials exist: end-to-end remote LLM generation and any non-zero token or cost accounting for hosted models.

Hallucination rule used by the script:
- A response is counted as hallucinated if it answers a refusal-required question without refusing.
- A response is also counted as hallucinated if it answers an answer-required question with missing/invalid citations or an answer that does not match the gold acceptable answers.

Load-test claim boundary:
- Do not claim concurrency capacity unless `experiments/metrics/load_test_report.json` shows a successful concurrency level.
- Do not claim RPS unless it was explicitly measured and selected for reporting.

## Current measured snapshot

From the run on March 8, 2026:
- Documents indexed: `2`
- Chunks indexed: `9`
- Vector index size on disk: `725156` bytes
- Dense retrieval latency: avg `16.226 ms`, p95 `30.329 ms`
- Hybrid retrieval latency: avg `7.194 ms`, p95 `8.058 ms`
- Retrieval at `k=5`: dense precision `0.2`, hybrid precision `0.2`, dense recall `0.7708`, hybrid recall `0.7708`
- Hallucination rate: dense baseline `0.2727`, strict grounded hybrid `0.0`
- Load test: no successful concurrency level measured in this run; see `experiments/metrics/load_test_report.json`

## Make targets
```bash
make stats
make eval-retrieval
make eval-grounding
make stability-60m
```

## Notes on common confusion
- `embedding_tokens = 0` is expected for local `sentence_transformers` backend because token accounting is not provided.
- `num_hits = 0` is usually threshold/filtering or missing index/path mismatch; use `/debug/retrieval` and `/stats` to prove where it drops.

## License
MIT
