from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_settings
from schemas.settings_api import AppSettingsResponse
from utils.settings import Settings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=AppSettingsResponse)
def app_settings(settings: Settings = Depends(get_settings)) -> AppSettingsResponse:  # noqa: B008
    default_mode = "hybrid_rrf" if settings.retrieval.hybrid.enabled else "dense"
    return AppSettingsResponse(
        app_name=settings.app.name,
        environment=settings.app.environment,
        default_generation_model=settings.generation.model,
        default_embedding_model=settings.embeddings.model,
        vector_store_provider=settings.vector_store.provider,
        auth_enabled=settings.auth.enabled,
        auth_provider=settings.auth.provider,
        summaries_enabled=settings.summaries.enabled,
        default_retrieval_mode=default_mode,
    )
