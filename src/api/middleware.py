from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from monitoring.metrics import REQUEST_LATENCY
from utils.logging import get_logger

log = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed = time.perf_counter() - start
            REQUEST_LATENCY.observe(elapsed)
            log.info(
                "http.request",
                request_id=request_id,
                method=request.method,
                path=str(request.url.path),
                elapsed_s=elapsed,
            )
