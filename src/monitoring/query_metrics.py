from __future__ import annotations

from monitoring.metrics import (
    AUTH_FAILURES,
    GENERATION_LATENCY,
    RATE_LIMIT_REJECTIONS,
    REQUEST_COST_USD,
    REQUEST_ERRORS,
    REQUEST_FALLBACKS,
    REQUEST_GROUNDED,
    REQUEST_LATENCY,
    REQUEST_REFUSALS,
    REQUEST_TOKENS,
    RERANK_LATENCY,
    RETRIEVAL_LATENCY,
    RETRIEVAL_TOP_GAP,
    RETRIEVAL_TOP_SCORE,
)
from schemas.response import SourceChunk


def record_usage_metrics(
    *,
    latency_s: float,
    retrieval_latency_s: float | None,
    generation_latency_s: float | None,
    embedding_tokens: int,
    llm_in: int | None,
    llm_out: int | None,
    total_cost: float | None,
    route: str,
    rerank_latency_s: float | None = None,
) -> None:
    REQUEST_LATENCY.observe(latency_s)
    if retrieval_latency_s is not None:
        RETRIEVAL_LATENCY.labels(route=route).observe(retrieval_latency_s)
    if rerank_latency_s is not None:
        RERANK_LATENCY.labels(route=route).observe(rerank_latency_s)
    if generation_latency_s is not None:
        GENERATION_LATENCY.labels(route=route).observe(generation_latency_s)
    if total_cost is not None:
        REQUEST_COST_USD.inc(total_cost)
    REQUEST_TOKENS.labels(kind="embedding").inc(float(embedding_tokens))
    if llm_in is not None:
        REQUEST_TOKENS.labels(kind="llm_in").inc(float(llm_in))
    if llm_out is not None:
        REQUEST_TOKENS.labels(kind="llm_out").inc(float(llm_out))


def record_error(stage: str) -> None:
    REQUEST_ERRORS.labels(stage=stage).inc()


def record_fallback(stage: str) -> None:
    REQUEST_FALLBACKS.labels(stage=stage).inc()


def record_refusal(reason: str) -> None:
    REQUEST_REFUSALS.labels(reason=reason.strip().lower() if reason else "unspecified").inc()


def record_grounded(answer: str, sources: list[SourceChunk], is_refusal: bool) -> None:
    if is_refusal:
        return
    REQUEST_GROUNDED.labels(
        grounded="true" if any(f"[{source.chunk_id}]" in answer for source in sources) else "false"
    ).inc()


def record_retrieval_scores(sources: list[SourceChunk]) -> None:
    if not sources:
        return
    RETRIEVAL_TOP_SCORE.observe(float(sources[0].score))
    if len(sources) > 1:
        RETRIEVAL_TOP_GAP.observe(max(0.0, float(sources[0].score) - float(sources[1].score)))


def record_auth_failure(reason: str) -> None:
    AUTH_FAILURES.labels(reason=reason).inc()


def record_rate_limit(path: str) -> None:
    RATE_LIMIT_REJECTIONS.labels(path=path).inc()
