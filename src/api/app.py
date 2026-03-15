from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.deps import get_retriever, get_settings, validate_runtime_readiness
from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from api.middleware import ObservabilityMiddleware
from api.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if os.environ.get("RAG_SKIP_STARTUP_VALIDATION", "0") != "1":
        validate_runtime_readiness()
        _ = get_retriever()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app.name,
        version="1.0.0",
        description=(
            "Production-style RAG API with strict grounding, hybrid retrieval, "
            "structured errors, Prometheus metrics, and versioned application routes."
        ),
        lifespan=lifespan,
        contact={"name": "rag-smart-qa contributors"},
    )
    app.state.settings = settings
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors.allow_origins,
        allow_credentials="*" not in settings.api.cors.allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(router)

    return app


app = create_app()
