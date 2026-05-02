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
    QUALITY_DRIFT_FLAG,
    RERANK_LATENCY,
    RETRIEVAL_FAILURES,
    RETRIEVAL_LATENCY,
    RETRIEVAL_TOP_GAP,
    RETRIEVAL_TOP_SCORE,
    VERIFIER_SCORE,
)
from schemas.response import SourceChunk

_QUALITY_WINDOW = 50
_retrieval_quality: list[float] = []
_answer_quality: list[float] = []


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


def record_retrieval_failure(reason: str | None) -> None:
    if reason:
        RETRIEVAL_FAILURES.labels(reason=reason).inc()


def record_verifier_score(score: float | None) -> None:
    if score is not None:
        VERIFIER_SCORE.observe(float(max(0.0, min(1.0, score))))


def record_quality_signal(
    *,
    retrieval_at_k: float | None,
    answer_accuracy: float | None,
) -> dict[str, object]:
    status: dict[str, object] = {
        "drift_detected": False,
        "signals": {},
        "suggestion": "",
    }

    def _append(window: list[float], value: float | None) -> float | None:
        if value is None:
            return None
        window.append(float(max(0.0, min(1.0, value))))
        del window[:-_QUALITY_WINDOW]
        return sum(window) / len(window)

    retrieval_avg = _append(_retrieval_quality, retrieval_at_k)
    answer_avg = _append(_answer_quality, answer_accuracy)
    retrieval_drift = retrieval_avg is not None and len(_retrieval_quality) >= 5 and retrieval_avg < 0.45
    answer_drift = answer_avg is not None and len(_answer_quality) >= 5 and answer_avg < 0.55
    QUALITY_DRIFT_FLAG.labels(signal="retrieval_at_k").set(1.0 if retrieval_drift else 0.0)
    QUALITY_DRIFT_FLAG.labels(signal="answer_accuracy").set(1.0 if answer_drift else 0.0)
    status["signals"] = {
        "retrieval_at_k_avg": retrieval_avg,
        "answer_accuracy_avg": answer_avg,
        "retrieval_samples": len(_retrieval_quality),
        "answer_samples": len(_answer_quality),
    }
    status["drift_detected"] = bool(retrieval_drift or answer_drift)
    if retrieval_drift and answer_drift:
        status["suggestion"] = "Retrieval and answer quality degraded; reindex corpus and review model/reranker calibration."
    elif retrieval_drift:
        status["suggestion"] = "Retrieval degraded; rebuild indexes or tune retrieval/reranking."
    elif answer_drift:
        status["suggestion"] = "Answer quality degraded; review prompts, verifier failures, or retrain/evaluate generation policy."
    return status


def record_auth_failure(reason: str) -> None:
    AUTH_FAILURES.labels(reason=reason).inc()


def record_rate_limit(path: str) -> None:
    RATE_LIMIT_REJECTIONS.labels(path=path).inc()
