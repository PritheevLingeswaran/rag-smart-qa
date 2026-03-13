from __future__ import annotations

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    document_id: str
    status: str
    title: str | None = None
    summary: str | None = None
    key_insights: list[str] = Field(default_factory=list)
    important_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    error_message: str | None = None
    method: str | None = None
    generated_at: str | None = None
