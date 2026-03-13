from __future__ import annotations

from fastapi import APIRouter

from api.routes.chat import router as chat_router
from api.routes.documents import router as documents_router
from api.routes.health import router as health_router
from api.routes.legacy import router as legacy_router
from api.routes.settings import router as settings_router
from api.routes.summaries import router as summaries_router

router = APIRouter()
router.include_router(health_router)
router.include_router(legacy_router)
router.include_router(documents_router)
router.include_router(chat_router)
router.include_router(summaries_router)
router.include_router(settings_router)
