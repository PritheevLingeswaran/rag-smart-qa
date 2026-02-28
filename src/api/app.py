from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_settings
from api.middleware import ObservabilityMiddleware
from api.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app.name)
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
