from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.deps import get_answerer, get_retriever
from monitoring.metrics import REQUEST_COST_USD, REQUEST_LATENCY, REQUEST_TOKENS
from schemas.query import HealthResponse, QueryRequest
from schemas.response import QueryResponse
from utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    retriever=Depends(get_retriever),
    answerer=Depends(get_answerer),
) -> QueryResponse:
    start = time.perf_counter()
    filter_sub = req.filter.source if req.filter and req.filter.source else None

    r = retriever.retrieve(
        question=req.query,
        top_k=req.top_k,
        filter_source_substr=filter_sub,
        rewrite_override=req.rewrite_query,
    )
    g = answerer.generate(req.query, r.hits)

    latency_s = time.perf_counter() - start
    REQUEST_LATENCY.observe(latency_s)

    total_cost = float(r.embedding_cost_usd + g.llm_cost_usd)
    REQUEST_COST_USD.inc(total_cost)
    REQUEST_TOKENS.labels(kind="embedding").inc(float(r.embedding_tokens))
    REQUEST_TOKENS.labels(kind="llm_in").inc(float(g.llm_tokens_in))
    REQUEST_TOKENS.labels(kind="llm_out").inc(float(g.llm_tokens_out))

    return QueryResponse(
        answer=g.answer,
        confidence=g.confidence,
        sources=g.sources,
        refusal=g.refusal,
        metrics={
            "query_used": r.query_used,
            "embedding_tokens": r.embedding_tokens,
            "embedding_cost_usd": r.embedding_cost_usd,
            "llm_tokens_in": g.llm_tokens_in,
            "llm_tokens_out": g.llm_tokens_out,
            "llm_cost_usd": g.llm_cost_usd,
            "total_cost_usd": total_cost,
            "num_hits": len(r.hits),
            "latency_ms": round(latency_s * 1000.0, 2),
        },
    )


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    data = generate_latest()
    return PlainTextResponse(data.decode("utf-8"), media_type=CONTENT_TYPE_LATEST)
