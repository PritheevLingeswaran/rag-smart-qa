from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DocumentFilter(BaseModel):
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
