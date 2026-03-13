from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.deps import get_answerer, get_retriever
from monitoring.metrics import (
    REQUEST_COST_USD,
    REQUEST_ERRORS,
    REQUEST_GROUNDED,
    REQUEST_LATENCY,
    REQUEST_REFUSALS,
    REQUEST_TOKENS,
    RETRIEVAL_TOP_GAP,
    RETRIEVAL_TOP_SCORE,
)
from schemas.query import QueryRequest
from schemas.response import QueryResponse, Refusal, SourceChunk
from utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["legacy"])


def _record_usage_metrics(
    *,
    latency_s: float,
    embedding_tokens: int,
    llm_in: int | None,
    llm_out: int | None,
    total_cost: float | None,
) -> None:
    REQUEST_LATENCY.observe(latency_s)
    if total_cost is not None:
        REQUEST_COST_USD.inc(total_cost)
    REQUEST_TOKENS.labels(kind="embedding").inc(float(embedding_tokens))
    if llm_in is not None:
        REQUEST_TOKENS.labels(kind="llm_in").inc(float(llm_in))
    if llm_out is not None:
        REQUEST_TOKENS.labels(kind="llm_out").inc(float(llm_out))


def _record_refusal(reason: str) -> None:
    REQUEST_REFUSALS.labels(reason=reason.strip().lower() if reason else "unspecified").inc()


def _record_grounded(answer: str, sources: list[SourceChunk], is_refusal: bool) -> None:
    if is_refusal:
        return
    REQUEST_GROUNDED.labels(
        grounded="true" if any(f"[{source.chunk_id}]" in answer for source in sources) else "false"
    ).inc()


def _record_retrieval_scores(sources: list[SourceChunk]) -> None:
    if not sources:
        return
    RETRIEVAL_TOP_SCORE.observe(float(sources[0].score))
    if len(sources) > 1:
        RETRIEVAL_TOP_GAP.observe(max(0.0, float(sources[0].score) - float(sources[1].score)))


def _to_source_chunks(hits: list[Any]) -> list[SourceChunk]:
    return [
        SourceChunk(
            chunk_id=hit.chunk.chunk_id,
            source=hit.chunk.source,
            page=hit.chunk.page,
            score=float(hit.score),
            text=hit.chunk.text,
        )
        for hit in hits
    ]


def _serialize_retrieval_hits(
    hits: list[Any], max_snippet_chars: int = 160
) -> list[dict[str, Any]]:
    return [
        {
            "doc_id": hit.chunk.chunk_id,
            "source": hit.chunk.source,
            "page": hit.chunk.page,
            "score": float(hit.score),
            "snippet": hit.chunk.text[:max_snippet_chars],
        }
        for hit in hits
    ]


@router.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    retriever: object = Depends(get_retriever),
    answerer: object = Depends(get_answerer),
) -> QueryResponse:
    start = time.perf_counter()
    filter_sub = req.filter.source if req.filter and req.filter.source else None
    if filter_sub and filter_sub.strip().lower() in {"string", "none", "null"}:
        filter_sub = None

    retriever_impl = cast(Any, retriever)
    answerer_impl = cast(Any, answerer)
    try:
        retrieval = retriever_impl.retrieve(
            question=req.query,
            top_k=req.top_k,
            filter_source_substr=filter_sub,
            rewrite_override=req.rewrite_query,
        )
    except Exception as exc:
        log.exception("query.retrieve_failed", error=str(exc))
        REQUEST_ERRORS.labels(stage="retrieval").inc()
        latency_s = time.perf_counter() - start
        _record_usage_metrics(
            latency_s=latency_s,
            embedding_tokens=0,
            llm_in=None,
            llm_out=None,
            total_cost=None,
        )
        _record_refusal("retrieval backend error")
        return QueryResponse(
            answer="I cannot answer right now because retrieval is temporarily unavailable.",
            confidence=0.0,
            sources=[],
            refusal=Refusal(
                is_refusal=True,
                reason="Retrieval backend error. Check model/API configuration and connectivity.",
            ),
            metrics={"error": "retrieval_failed", "latency_ms": round(latency_s * 1000.0, 2)},
        )

    try:
        generation = answerer_impl.generate(req.query, retrieval.hits)
    except Exception as exc:
        log.exception("query.generate_failed", error=str(exc))
        REQUEST_ERRORS.labels(stage="generation").inc()
        latency_s = time.perf_counter() - start
        total_cost = float(retrieval.embedding_cost_usd)
        _record_usage_metrics(
            latency_s=latency_s,
            embedding_tokens=int(retrieval.embedding_tokens),
            llm_in=None,
            llm_out=None,
            total_cost=total_cost,
        )
        _record_refusal("generation backend error")
        return QueryResponse(
            answer="I found relevant sources, but answer generation is temporarily unavailable.",
            confidence=0.0,
            sources=_to_source_chunks(retrieval.hits),
            refusal=Refusal(
                is_refusal=True,
                reason="Generation backend error. Check model/API configuration and connectivity.",
            ),
            metrics={
                "query_used": retrieval.query_used,
                "embedding_tokens": retrieval.embedding_tokens,
                "embedding_cost_usd": retrieval.embedding_cost_usd,
                "llm_tokens_in": None,
                "llm_tokens_out": None,
                "llm_cost_usd": None,
                "total_cost_usd": total_cost,
                "num_hits": len(retrieval.hits),
                "error": "generation_failed",
                "latency_ms": round(latency_s * 1000.0, 2),
            },
        )

    latency_s = time.perf_counter() - start
    total_cost = (
        float(retrieval.embedding_cost_usd + float(generation.llm_cost_usd or 0.0))
        if generation.llm_cost_usd is not None
        else None
    )
    _record_usage_metrics(
        latency_s=latency_s,
        embedding_tokens=int(retrieval.embedding_tokens),
        llm_in=generation.llm_tokens_in,
        llm_out=generation.llm_tokens_out,
        total_cost=total_cost,
    )
    _record_retrieval_scores(generation.sources)
    if generation.refusal.is_refusal:
        _record_refusal(generation.refusal.reason)
    _record_grounded(generation.answer, generation.sources, generation.refusal.is_refusal)
    return QueryResponse(
        answer=generation.answer,
        confidence=generation.confidence,
        sources=generation.sources,
        refusal=generation.refusal,
        metrics={
            "query_used": retrieval.query_used,
            "embedding_tokens": retrieval.embedding_tokens,
            "embedding_cost_usd": retrieval.embedding_cost_usd,
            "llm_tokens_in": generation.llm_tokens_in,
            "llm_tokens_out": generation.llm_tokens_out,
            "llm_cost_usd": generation.llm_cost_usd,
            "total_cost_usd": total_cost,
            "num_hits": len(retrieval.hits),
            "latency_ms": round(latency_s * 1000.0, 2),
            "answerability": generation.answerability,
            "citation_coverage": generation.citation_coverage,
            "cost_measured": generation.llm_cost_usd is not None,
        },
    )


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@router.get("/stats")
def stats(retriever: object = Depends(get_retriever)) -> dict[str, Any]:
    retriever_impl = cast(Any, retriever)
    settings = retriever_impl.settings
    store = retriever_impl.store
    chunks_path = Path(settings.paths.chunks_dir) / "chunks.jsonl"
    docs: set[str] = set()
    chunks_count = 0
    if chunks_path.exists():
        with chunks_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                chunks_count += 1
                try:
                    source = cast(str, json.loads(line).get("source", ""))
                except Exception:
                    source = ""
                if source:
                    docs.add(source)
    vector_count = 0
    if hasattr(store, "_collection"):
        try:
            vector_count = int(store._collection.count())  # type: ignore[attr-defined]
        except Exception:
            vector_count = 0
    elif hasattr(store, "index") and getattr(store, "index", None) is not None:
        try:
            vector_count = int(store.index.ntotal)  # type: ignore[attr-defined]
        except Exception:
            vector_count = 0
    return {
        "environment": settings.app.environment,
        "provider": settings.vector_store.provider,
        "paths": {
            "chunks_path": str(chunks_path),
            "bm25_dir": str(Path(settings.paths.indexes_dir) / "bm25"),
        },
        "corpus": {
            "docs_count": len(docs),
            "chunks_count": chunks_count,
            "vector_count": vector_count,
        },
    }


@router.post("/retrieve/bm25")
def retrieve_bm25(req: QueryRequest, retriever: object = Depends(get_retriever)) -> dict[str, Any]:
    retriever_impl = cast(Any, retriever)
    filter_sub = req.filter.source if req.filter and req.filter.source else None
    retrieval = retriever_impl.retrieve_with_debug(
        question=req.query,
        top_k=req.top_k,
        filter_source_substr=filter_sub,
        rewrite_override=req.rewrite_query,
        mode_override="bm25",
    )
    hits = _serialize_retrieval_hits(retrieval.hits)
    return {
        "query_used": retrieval.query_used,
        "doc_ids": [hit["doc_id"] for hit in hits],
        "hits": hits,
        "num_hits": len(hits),
        "debug": retrieval.debug,
    }


@router.post("/retrieve/hybrid")
def retrieve_hybrid(
    req: QueryRequest, retriever: object = Depends(get_retriever)
) -> dict[str, Any]:
    retriever_impl = cast(Any, retriever)
    filter_sub = req.filter.source if req.filter and req.filter.source else None
    retrieval = retriever_impl.retrieve_with_debug(
        question=req.query,
        top_k=req.top_k,
        filter_source_substr=filter_sub,
        rewrite_override=req.rewrite_query,
        mode_override="hybrid",
    )
    hits = _serialize_retrieval_hits(retrieval.hits)
    return {
        "query_used": retrieval.query_used,
        "doc_ids": [hit["doc_id"] for hit in hits],
        "hits": hits,
        "num_hits": len(hits),
        "embedding_tokens": retrieval.embedding_tokens,
        "embedding_cost_usd": retrieval.embedding_cost_usd,
        "debug": retrieval.debug,
    }


@router.post("/debug/retrieval")
def debug_retrieval(
    req: QueryRequest, retriever: object = Depends(get_retriever)
) -> dict[str, Any]:
    retriever_impl = cast(Any, retriever)
    env_enabled = os.environ.get("RAG_DEBUG_RETRIEVAL", "0").lower() in {"1", "true", "yes"}
    cfg_enabled = bool(retriever_impl.settings.api.enable_debug_retrieval_endpoint)
    if not (cfg_enabled or env_enabled):
        return {
            "enabled": False,
            "message": "Set api.enable_debug_retrieval_endpoint=true or RAG_DEBUG_RETRIEVAL=1.",
        }
    filter_sub = req.filter.source if req.filter and req.filter.source else None
    retrieval = retriever_impl.retrieve_with_debug(
        question=req.query,
        top_k=req.top_k,
        filter_source_substr=filter_sub,
        rewrite_override=req.rewrite_query,
        mode_override="hybrid",
    )
    return {
        "enabled": True,
        "query_used": retrieval.query_used,
        "embedding_tokens": retrieval.embedding_tokens,
        "embedding_cost_usd": retrieval.embedding_cost_usd,
        "num_hits": len(retrieval.hits),
        "doc_ids": [hit.chunk.chunk_id for hit in retrieval.hits],
        "scores": [float(hit.score) for hit in retrieval.hits],
        "debug": retrieval.debug,
    }
