from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from utils.settings import RateLimitConfig


class InMemoryRateLimiter:
    def __init__(self, cfg: RateLimitConfig) -> None:
        self.cfg = cfg
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0
        limit = int(self.cfg.requests_per_minute) + int(self.cfg.burst)
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(bucket[0] + 60.0 - now))
                return False, retry_after
            bucket.append(now)
            return True, 0
