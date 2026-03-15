from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TypeVar

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="rag-timeout")
T = TypeVar("T")


class StageTimeoutError(TimeoutError):
    def __init__(self, stage: str, timeout_s: float) -> None:
        super().__init__(f"{stage} timed out after {timeout_s:.2f}s")
        self.stage = stage
        self.timeout_s = timeout_s


def run_with_timeout(stage: str, timeout_s: float, fn: Callable[[], T]) -> T:
    future = _executor.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FutureTimeoutError as exc:
        future.cancel()
        raise StageTimeoutError(stage, timeout_s) from exc
