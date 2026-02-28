from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from evaluation.performance import summarize_latency
from utils.config import load_settings


def _load_questions(dataset_path: str) -> list[str]:
    p = Path(dataset_path)
    if not p.exists():
        return []
    qs: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            q = str(obj.get("question", "")).strip()
            if q:
                qs.append(q)
        except Exception:
            continue
    return qs


@dataclass
class LoadResult:
    ok: bool
    latency_s: float
    status_code: int
    error: str | None = None


async def _one_request(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    timeout_s: float,
) -> LoadResult:
    t0 = time.perf_counter()
    try:
        r = await client.post(url, json=payload, timeout=timeout_s)
        lat = time.perf_counter() - t0
        ok = 200 <= r.status_code < 300
        return LoadResult(
            ok=ok, latency_s=lat, status_code=r.status_code, error=None if ok else r.text[:200]
        )
    except Exception as e:
        lat = time.perf_counter() - t0
        return LoadResult(ok=False, latency_s=lat, status_code=0, error=str(e))


async def load_test_async() -> None:
    settings = load_settings()
    lt = settings.load_test

    base_url = lt.base_url.rstrip("/")
    endpoint = lt.endpoint if lt.endpoint.startswith("/") else "/" + lt.endpoint
    url = base_url + endpoint

    questions = _load_questions(settings.evaluation.dataset_path) if lt.use_eval_questions else []
    if not questions:
        # Fallback question to keep the tool usable with any corpus.
        questions = ["Summarize the key points in the documents."]

    total = int(max(1, lt.total_requests))
    conc = int(max(1, lt.concurrency))
    timeout_s = float(max(1.0, lt.timeout_s))

    # Use a shared client to simulate real load (connection reuse).
    limits = httpx.Limits(max_keepalive_connections=conc, max_connections=conc)
    async with httpx.AsyncClient(limits=limits) as client:
        sem = asyncio.Semaphore(conc)
        results: list[LoadResult] = []

        async def runner(i: int) -> None:
            q = random.choice(questions)
            payload = {"query": q, "top_k": settings.vector_store.top_k}
            async with sem:
                res = await _one_request(client, url, payload, timeout_s)
                results.append(res)

        t0 = time.perf_counter()
        await asyncio.gather(*[runner(i) for i in range(total)])
        wall = time.perf_counter() - t0

    oks = [r for r in results if r.ok]
    errs = [r for r in results if not r.ok]
    lats = [r.latency_s for r in results]
    ok_lats = [r.latency_s for r in oks] if oks else lats

    stats = summarize_latency(ok_lats)
    throughput = (len(oks) / wall) if wall > 0 else 0.0
    success_rate = (len(oks) / len(results)) if results else 0.0

    out_json = {
        "base_url": base_url,
        "endpoint": endpoint,
        "concurrency": conc,
        "total_requests": total,
        "wall_time_s": wall,
        "throughput_rps": throughput,
        "success_rate": success_rate,
        "p50_latency_ms": stats.p50_ms,
        "p95_latency_ms": stats.p95_ms,
        "p99_latency_ms": stats.p99_ms,
        "avg_latency_ms": stats.avg_ms,
        "error_count": len(errs),
        "sample_errors": [e.error for e in errs[:5]],
    }

    Path("docs").mkdir(parents=True, exist_ok=True)
    Path("docs/load_test_results.json").write_text(json.dumps(out_json, indent=2), encoding="utf-8")
    md = (
        "# Load Test Results\n\n"
        f"Target: `{url}`\n\n"
        "## Summary\n"
        f"- concurrency: {conc}\n"
        f"- total requests: {total}\n"
        f"- wall time (s): {wall:.2f}\n"
        f"- throughput (RPS): {throughput:.2f}\n"
        f"- success rate: {success_rate:.3f}\n\n"
        "## Latency (successful requests)\n"
        f"- p50 (ms): {stats.p50_ms:.2f}\n"
        f"- p95 (ms): {stats.p95_ms:.2f}\n"
        f"- p99 (ms): {stats.p99_ms:.2f}\n"
        f"- avg (ms): {stats.avg_ms:.2f}\n\n"
        "## Errors\n"
        f"- error count: {len(errs)}\n"
        f"- sample errors: {out_json['sample_errors']}\n"
    )
    Path("docs/load_test_results.md").write_text(md, encoding="utf-8")

    print(md)


def load_test_main() -> None:
    """Run a lightweight HTTP load test.

    How to interpret the output:
    - Treat this as a *smoke* load test, not a full capacity plan.
    - Increase concurrency/total_requests to find the knee point (p95 spikes or errors appear).
    """

    asyncio.run(load_test_async())


if __name__ == "__main__":
    load_test_main()
