from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    detail: str
    code: str = "request_error"


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
    created_at: str


class PreviewPage(BaseModel):
    page: int
    text: str


class ChunkPreview(BaseModel):
    chunk_id: str
    page: int
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
