from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float = Field(ge=-1.0, le=1.0)
    text: str


class Refusal(BaseModel):
    is_refusal: bool
    reason: str


class QueryResponse(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[SourceChunk]
    refusal: Refusal
    metrics: dict[str, Any] = Field(default_factory=dict)
