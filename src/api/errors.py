from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.api_common import ApiErrorResponse, ErrorDetail
from utils.logging import get_logger

log = get_logger(__name__)


def build_error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = ApiErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=request_id,
            details=details or {},
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message", detail.get("detail", "Request failed.")))
        code = str(detail.get("code", "http_error"))
        details: dict[str, Any] = {
            str(k): v for k, v in detail.items() if k not in {"message", "detail", "code"}
        }
    else:
        message = str(detail)
        code = "http_error"
        details = {}
    return build_error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return build_error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        details={"errors": jsonable_encoder(exc.errors())},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("http.unhandled_exception", error=str(exc), path=str(request.url.path))
    return build_error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message="Internal server error.",
    )
