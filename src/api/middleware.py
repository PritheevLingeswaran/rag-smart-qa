from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import ClassVar

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from api.errors import build_error_response
from api.rate_limit import InMemoryRateLimiter
from monitoring.metrics import HTTP_REQUEST_LATENCY, REQUEST_COUNT
from monitoring.query_metrics import record_error, record_rate_limit
from services.auth_service import AuthService
from utils.logging import get_logger
from utils.settings import Settings

log = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    _rate_limiters: ClassVar[dict[int, InMemoryRateLimiter]] = {}

    @classmethod
    def _get_limiter(cls, settings: Settings) -> InMemoryRateLimiter:
        key = id(settings)
        limiter = cls._rate_limiters.get(key)
        if limiter is None:
            limiter = InMemoryRateLimiter(settings.monitoring.rate_limit)
            cls._rate_limiters[key] = limiter
        return limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = request.app.state.settings
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        correlation_id = request.headers.get("x-correlation-id", request_id)
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        bind_contextvars(request_id=request_id, correlation_id=correlation_id)
        start = time.perf_counter()
        response: Response | None = None
        exc: Exception | None = None
        status_code = "500"
        try:
            log.info(
                "http.request.started",
                method=request.method,
                path=str(request.url.path),
                client_ip=_client_ip(request),
            )
            maybe_rejected = self._reject_unauthorized_or_limited(request, settings)
            if maybe_rejected is not None:
                response = maybe_rejected
            else:
                response = await call_next(request)
            status_code = str(response.status_code)
        except HTTPException as e:
            response = build_error_response(
                request=request,
                status_code=e.status_code,
                code=str(e.detail.get("code", "http_error"))
                if isinstance(e.detail, dict)
                else "http_error",
                message=(
                    str(e.detail.get("message", e.detail.get("detail", "Request failed.")))
                    if isinstance(e.detail, dict)
                    else str(e.detail)
                ),
                details=(
                    {
                        str(k): v
                        for k, v in e.detail.items()
                        if k not in {"code", "message", "detail"}
                    }
                    if isinstance(e.detail, dict)
                    else None
                ),
            )
            status_code = str(e.status_code)
        except Exception as e:  # pragma: no cover - passthrough path
            exc = e
            log.exception(
                "http.request.failed",
                method=request.method,
                path=str(request.url.path),
                error=str(e),
            )
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_COUNT.labels(path=str(request.url.path), status_code=status_code).inc()
            HTTP_REQUEST_LATENCY.labels(
                method=request.method,
                path=str(request.url.path),
                status_code=status_code,
            ).observe(elapsed)
            log.info(
                "http.request",
                request_id=request_id,
                correlation_id=correlation_id,
                method=request.method,
                path=str(request.url.path),
                elapsed_s=elapsed,
                status_code=status_code,
            )
            clear_contextvars()
        if exc is not None:
            raise exc
        if response is None:  # pragma: no cover - defensive
            raise RuntimeError("Request handling failed before a response was created")
        response.headers["x-request-id"] = request_id
        response.headers["x-correlation-id"] = correlation_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "same-origin"
        return response

    def _reject_unauthorized_or_limited(
        self,
        request: Request,
        settings: Settings,
    ) -> Response | None:
        path = str(request.url.path)
        if not _is_exempt_path(path, settings.auth.exempt_paths):
            auth_service = AuthService(settings)
            api_key = request.headers.get(settings.auth.api_key_header)
            auth_service.authenticate_api_key(api_key)
        if settings.monitoring.rate_limit.enabled and not _is_exempt_path(
            path, settings.monitoring.rate_limit.exempt_paths
        ):
            limiter = self._get_limiter(settings)
            key = _rate_limit_key(request, settings)
            allowed, retry_after = limiter.allow(key)
            if not allowed:
                record_rate_limit(path)
                record_error("rate_limit")
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests. Please retry later.",
                            "request_id": getattr(request.state, "request_id", None),
                            "details": {"retry_after_seconds": retry_after},
                        }
                    },
                )
                response.headers["retry-after"] = str(retry_after)
                return response
        return None


def _is_exempt_path(path: str, exempt_paths: list[str]) -> bool:
    return any(path == exempt or path.startswith(f"{exempt}/") for exempt in exempt_paths)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _rate_limit_key(request: Request, settings: Settings) -> str:
    if settings.monitoring.rate_limit.key_strategy == "user_or_ip":
        user_id = request.headers.get(settings.auth.header_user_id)
        if user_id:
            return f"user:{user_id}"
    return f"ip:{_client_ip(request)}"
