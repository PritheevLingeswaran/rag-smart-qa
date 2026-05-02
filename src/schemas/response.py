from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float
    text: str
    dense_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    final_rank_reason: str | None = None
    retrieval_explanation: dict[str, Any] = Field(default_factory=dict)


class Refusal(BaseModel):
    is_refusal: bool
    reason: str


class QueryResponse(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[SourceChunk]
    refusal: Refusal
    metrics: dict[str, Any] = Field(default_factory=dict)
