from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from schemas.api_common import SourceCitation


class ChatQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    retrieval_mode: Literal[
        "dense",
        "bm25",
        "hybrid_weighted",
        "hybrid_rrf",
        "hybrid_rrf_rerank",
    ] = "hybrid_rrf"
    top_k: int = Field(default=8, ge=1, le=25)


class ChatResponseSource(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float
    text: str


class ChatQueryResponse(BaseModel):
    session_id: str
    answer: str
    confidence: float
    refusal: dict[str, object]
    citations: list[SourceCitation]
    sources: list[ChatResponseSource]
    timing: dict[str, object] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    confidence: float | None = None
    refusal: bool = False
    latency_ms: float | None = None
    created_at: str
    metadata: dict[str, object] = Field(default_factory=dict)


class ChatSession(BaseModel):
    id: str
    owner_id: str
    title: str
    created_at: str
    updated_at: str


class ChatSessionDetail(ChatSession):
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSession]
