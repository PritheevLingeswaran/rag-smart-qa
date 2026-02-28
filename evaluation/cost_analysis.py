from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostStats:
    avg_cost_usd: float
    p95_cost_usd: float
    total_cost_usd: float


def summarize_cost(costs: list[float]) -> CostStats:
    if not costs:
        return CostStats(avg_cost_usd=0.0, p95_cost_usd=0.0, total_cost_usd=0.0)
    s = sorted(costs)
    total = sum(s)
    avg = total / len(s)
    p95 = s[int(0.95 * (len(s) - 1))]
    return CostStats(avg_cost_usd=avg, p95_cost_usd=p95, total_cost_usd=total)
