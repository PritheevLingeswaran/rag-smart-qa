from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = "request_error"
    message: str
    request_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    error: ErrorDetail


class PaginationMeta(BaseModel):
    total: int


class SourceCitation(BaseModel):
    id: str
    document_id: str | None = None
    chunk_id: str
    source: str
    page: int
    excerpt: str
    score: float
    dense_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    final_rank_reason: str | None = None
    retrieval_explanation: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class PreviewPage(BaseModel):
    page: int
    text: str


class ChunkPreview(BaseModel):
    chunk_id: str
    page: int
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
