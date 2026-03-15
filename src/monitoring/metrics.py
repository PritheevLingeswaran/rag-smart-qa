from __future__ import annotations

from prometheus_client import Counter, Histogram

HTTP_REQUEST_LATENCY = Histogram(
    "rag_http_request_latency_seconds",
    "Latency of HTTP requests by method and path",
    ["method", "path", "status_code"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
REQUEST_LATENCY = Histogram(
    "rag_request_latency_seconds",
    "Latency for /query requests",
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10),
)
RETRIEVAL_LATENCY = Histogram(
    "rag_retrieval_latency_seconds",
    "Latency of the retrieval stage",
    ["route"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2),
)
GENERATION_LATENCY = Histogram(
    "rag_generation_latency_seconds",
    "Latency of the answer generation stage",
    ["route"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
RERANK_LATENCY = Histogram(
    "rag_rerank_latency_seconds",
    "Latency of the reranking stage",
    ["route"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2),
)
REQUEST_COST_USD = Counter("rag_request_cost_usd_total", "Total USD cost across requests")
REQUEST_TOKENS = Counter("rag_request_tokens_total", "Total tokens used across requests", ["kind"])
REQUEST_COUNT = Counter(
    "rag_http_requests_total",
    "Total HTTP requests by path and status code",
    ["path", "status_code"],
)
REQUEST_ERRORS = Counter(
    "rag_request_errors_total",
    "Total query pipeline errors by stage",
    ["stage"],
)
REQUEST_REFUSALS = Counter(
    "rag_refusals_total",
    "Total query refusals",
    ["reason"],
)
REQUEST_GROUNDED = Counter(
    "rag_grounded_answers_total",
    "Total grounded answers and non-grounded answers",
    ["grounded"],
)
RETRIEVAL_TOP_SCORE = Histogram(
    "rag_retrieval_top_score",
    "Top retrieval score observed per query",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)
RETRIEVAL_TOP_GAP = Histogram(
    "rag_retrieval_top_gap",
    "Score gap between top-1 and top-2 retrieval hits",
    buckets=(0.0, 0.01, 0.03, 0.05, 0.08, 0.12, 0.2, 0.4, 1.0),
)
REQUEST_FALLBACKS = Counter(
    "rag_fallback_responses_total",
    "Total degraded or fallback responses emitted by the application",
    ["stage"],
)
AUTH_FAILURES = Counter(
    "rag_auth_failures_total",
    "Total authentication failures by reason",
    ["reason"],
)
RATE_LIMIT_REJECTIONS = Counter(
    "rag_rate_limit_rejections_total",
    "Total requests rejected by in-memory rate limiting",
    ["path"],
)
