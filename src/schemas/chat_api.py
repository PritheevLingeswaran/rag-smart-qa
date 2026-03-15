from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from schemas.api_common import SourceCitation
from schemas.response import Refusal


class ChatQueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
        examples=["Summarize the monitoring implementation in this workspace."],
    )
    session_id: str | None = None
    retrieval_mode: Literal[
        "dense",
        "bm25",
        "hybrid_weighted",
        "hybrid_rrf",
        "hybrid_rrf_rerank",
    ] = "hybrid_rrf"
    top_k: int = Field(default=8, ge=1, le=25)

    @field_validator("question")
    @classmethod
    def _validate_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question must not be empty or whitespace only.")
        return normalized


class ChatResponseSource(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float
    text: str


class ChatTiming(BaseModel):
    total_latency_ms: float | None = None
    retrieval_latency_ms: float | None = None
    rerank_latency_ms: float | None = None
    generation_latency_ms: float | None = None
    embedding_tokens: int | None = None
    embedding_cost_usd: float | None = None
    llm_tokens_in: int | None = None
    llm_tokens_out: int | None = None
    llm_cost_usd: float | None = None


class ChatQueryResponse(BaseModel):
    session_id: str
    answer: str
    confidence: float
    refusal: Refusal
    citations: list[SourceCitation]
    sources: list[ChatResponseSource]
    timing: ChatTiming = Field(default_factory=ChatTiming)


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
