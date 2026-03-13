from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_document_service, validate_runtime_readiness
from schemas.query import HealthResponse
from services.document_service import DocumentService

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
@router.get("/readiness", response_model=HealthResponse)
def readiness(
    document_service: DocumentService = Depends(get_document_service),  # noqa: B008
) -> HealthResponse:
    try:
        validate_runtime_readiness()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _ = document_service
    return HealthResponse(status="ok")
