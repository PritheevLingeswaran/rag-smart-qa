from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


def percentile(values: Iterable[float], p: float) -> float:
    """Compute percentile using linear interpolation.

    Why we implement this ourselves:
    - Avoid adding heavy dependencies (numpy/pandas) in a core eval path.
    - Deterministic and easy to test.
    """

    xs: list[float] = sorted([float(v) for v in values])
    if not xs:
        return 0.0
    if p <= 0:
        return xs[0]
    if p >= 100:
        return xs[-1]

    # index in [0, n-1]
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    d0 = xs[f] * (c - k)
    d1 = xs[c] * (k - f)
    return d0 + d1


@dataclass
class LatencyStats:
    n: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


def summarize_latency(latencies_s: Iterable[float]) -> LatencyStats:
    xs = [float(x) for x in latencies_s]
    n = len(xs)
    if n == 0:
        return LatencyStats(n=0, avg_ms=0.0, p50_ms=0.0, p95_ms=0.0, p99_ms=0.0)

    avg_ms = (sum(xs) / n) * 1000.0
    p50_ms = percentile(xs, 50.0) * 1000.0
    p95_ms = percentile(xs, 95.0) * 1000.0
    p99_ms = percentile(xs, 99.0) * 1000.0
    return LatencyStats(n=n, avg_ms=avg_ms, p50_ms=p50_ms, p95_ms=p95_ms, p99_ms=p99_ms)
