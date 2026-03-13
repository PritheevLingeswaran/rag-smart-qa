from __future__ import annotations

from pydantic import BaseModel


class AppSettingsResponse(BaseModel):
    app_name: str
    environment: str
    default_generation_model: str
    default_embedding_model: str
    vector_store_provider: str
    auth_enabled: bool
    auth_provider: str
    summaries_enabled: bool
    default_retrieval_mode: str
