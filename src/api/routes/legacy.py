from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.deps import get_answerer, get_retriever, get_settings
from monitoring.query_metrics import (
    record_error,
    record_fallback,
    record_grounded,
    record_refusal,
    record_retrieval_scores,
    record_usage_metrics,
)
from schemas.query import QueryRequest
from schemas.response import QueryResponse, Refusal, SourceChunk
from utils.logging import get_logger
from utils.timeout import StageTimeoutError, run_with_timeout

log = get_logger(__name__)
router = APIRouter(tags=["legacy"])


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
    settings = getattr(retriever_impl, "settings", get_settings())
    retrieval_started = time.perf_counter()
    try:
        retrieval = run_with_timeout(
            "retrieval",
            float(settings.api.retrieval_timeout_s),
            lambda: retriever_impl.retrieve(
                question=req.query,
                top_k=req.top_k,
                filter_source_substr=filter_sub,
                rewrite_override=req.rewrite_query,
            ),
        )
    except StageTimeoutError as exc:
        log.warning("query.retrieve_timeout", error=str(exc))
        record_error("retrieval_timeout")
        record_fallback("legacy_retrieval_timeout")
        latency_s = time.perf_counter() - start
        record_usage_metrics(
            latency_s=latency_s,
            retrieval_latency_s=time.perf_counter() - retrieval_started,
            generation_latency_s=None,
            embedding_tokens=0,
            llm_in=None,
            llm_out=None,
            total_cost=None,
            route="/query",
        )
        record_refusal("retrieval timed out")
        return QueryResponse(
            answer="I cannot answer right now because retrieval timed out.",
            confidence=0.0,
            sources=[],
            refusal=Refusal(is_refusal=True, reason="Retrieval timed out."),
            metrics={"error": "retrieval_timeout", "latency_ms": round(latency_s * 1000.0, 2)},
        )
    except Exception as exc:
        log.exception("query.retrieve_failed", error=str(exc))
        record_error("retrieval")
        record_fallback("legacy_retrieval_failed")
        latency_s = time.perf_counter() - start
        record_usage_metrics(
            latency_s=latency_s,
            retrieval_latency_s=time.perf_counter() - retrieval_started,
            generation_latency_s=None,
            embedding_tokens=0,
            llm_in=None,
            llm_out=None,
            total_cost=None,
            route="/query",
        )
        record_refusal("retrieval backend error")
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

    retrieval_latency_s = time.perf_counter() - retrieval_started
    generation_started = time.perf_counter()
    try:
        generation = run_with_timeout(
            "generation",
            float(settings.api.generation_timeout_s),
            lambda: answerer_impl.generate(req.query, retrieval.hits),
        )
    except StageTimeoutError as exc:
        log.warning("query.generate_timeout", error=str(exc))
        record_error("generation_timeout")
        record_fallback("legacy_generation_timeout")
        latency_s = time.perf_counter() - start
        generation_latency_s = time.perf_counter() - generation_started
        failed_total_cost = float(retrieval.embedding_cost_usd)
        record_usage_metrics(
            latency_s=latency_s,
            retrieval_latency_s=retrieval_latency_s,
            generation_latency_s=generation_latency_s,
            embedding_tokens=int(retrieval.embedding_tokens),
            llm_in=None,
            llm_out=None,
            total_cost=failed_total_cost,
            route="/query",
        )
        record_refusal("generation timed out")
        return QueryResponse(
            answer="I found relevant sources, but answer generation timed out.",
            confidence=0.0,
            sources=_to_source_chunks(retrieval.hits),
            refusal=Refusal(is_refusal=True, reason="Generation timed out."),
            metrics={
                "query_used": retrieval.query_used,
                "embedding_tokens": retrieval.embedding_tokens,
                "embedding_cost_usd": retrieval.embedding_cost_usd,
                "num_hits": len(retrieval.hits),
                "error": "generation_timeout",
                "latency_ms": round(latency_s * 1000.0, 2),
            },
        )
    except Exception as exc:
        log.exception("query.generate_failed", error=str(exc))
        record_error("generation")
        record_fallback("legacy_generation_failed")
        latency_s = time.perf_counter() - start
        failed_total_cost = float(retrieval.embedding_cost_usd)
        generation_latency_s = time.perf_counter() - generation_started
        record_usage_metrics(
            latency_s=latency_s,
            retrieval_latency_s=retrieval_latency_s,
            generation_latency_s=generation_latency_s,
            embedding_tokens=int(retrieval.embedding_tokens),
            llm_in=None,
            llm_out=None,
            total_cost=failed_total_cost,
            route="/query",
        )
        record_refusal("generation backend error")
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
                "total_cost_usd": failed_total_cost,
                "num_hits": len(retrieval.hits),
                "error": "generation_failed",
                "latency_ms": round(latency_s * 1000.0, 2),
            },
        )

    latency_s = time.perf_counter() - start
    generation_latency_s = time.perf_counter() - generation_started
    retrieval_debug = getattr(retrieval, "debug", None)
    rerank_latency_ms = (
        float(cast(dict[str, Any], retrieval_debug).get("timings_ms", {}).get("rerank"))
        if retrieval_debug
        and cast(dict[str, Any], retrieval_debug).get("timings_ms", {}).get("rerank") is not None
        else None
    )
    total_cost: float | None = (
        float(retrieval.embedding_cost_usd + float(generation.llm_cost_usd or 0.0))
        if generation.llm_cost_usd is not None
        else None
    )
    record_usage_metrics(
        latency_s=latency_s,
        retrieval_latency_s=retrieval_latency_s,
        generation_latency_s=generation_latency_s,
        embedding_tokens=int(retrieval.embedding_tokens),
        llm_in=generation.llm_tokens_in,
        llm_out=generation.llm_tokens_out,
        total_cost=total_cost,
        route="/query",
        rerank_latency_s=(rerank_latency_ms / 1000.0) if rerank_latency_ms is not None else None,
    )
    record_retrieval_scores(generation.sources)
    if generation.refusal.is_refusal:
        record_refusal(generation.refusal.reason)
    record_grounded(generation.answer, generation.sources, generation.refusal.is_refusal)
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
            "retrieval_latency_ms": round(retrieval_latency_s * 1000.0, 2),
            "generation_latency_ms": round(generation_latency_s * 1000.0, 2),
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
