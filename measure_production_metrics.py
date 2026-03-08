import argparse
import asyncio
import csv
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import httpx


# ----------------------------
# Utility: metrics
# ----------------------------
def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    if k <= 0:
        return 0.0
    rel = set(relevant)
    topk = retrieved[:k]
    return sum(1 for x in topk if x in rel) / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    rel = set(relevant)
    if not rel:
        return 0.0
    topk = retrieved[:k]
    return sum(1 for x in topk if x in rel) / len(rel)


def pct_improvement(new: float, base: float) -> float:
    if base == 0:
        return float("inf") if new > 0 else 0.0
    return (new - base) / base * 100.0


def p(arr: List[float], q: float) -> float:
    if not arr:
        return float("nan")
    return float(np.percentile(np.array(arr, dtype=float), q))


# ----------------------------
# Corpus size: FAISS / Chroma
# ----------------------------
def get_faiss_ntotal(index_path: str) -> int:
    import faiss  # type: ignore
    index = faiss.read_index(index_path)
    return int(index.ntotal)


def get_chroma_count(persist_dir: str, collection_name: str) -> Tuple[int, Optional[int]]:
    import chromadb  # type: ignore

    client = chromadb.PersistentClient(path=persist_dir)
    col = client.get_collection(collection_name)
    chunk_count = int(col.count())

    # Try to estimate doc count via metadata doc_id if present
    doc_count = None
    try:
        # This can be heavy if you have millions of chunks; OK for student projects.
        res = col.get(include=["metadatas"])
        metas = res.get("metadatas") or []
        doc_ids = set()
        for m in metas:
            if isinstance(m, dict) and "doc_id" in m and m["doc_id"] is not None:
                doc_ids.add(str(m["doc_id"]))
        if doc_ids:
            doc_count = len(doc_ids)
    except Exception:
        doc_count = None

    return chunk_count, doc_count


# ----------------------------
# Retrieval via HTTP endpoints
# ----------------------------
async def call_retriever(
    client: httpx.AsyncClient,
    url: str,
    method: str,
    payload_template: Dict[str, Any],
    query: str,
    timeout_s: float,
) -> Dict[str, Any]:
    payload = dict(payload_template)
    payload["query"] = query

    if method.upper() == "GET":
        r = await client.get(url, params=payload, timeout=timeout_s)
    else:
        r = await client.request(method.upper(), url, json=payload, timeout=timeout_s)

    r.raise_for_status()
    return cast(Dict[str, Any], r.json())


def extract_doc_ids(resp_json: Dict[str, Any]) -> List[str]:
    """
    You MUST adapt this mapping to your API response.

    Common patterns:
    - resp["doc_ids"] -> list[str]
    - resp["retrieved"] -> list[{"doc_id": "..."}]
    - resp["sources"] -> list[{"doc_id": "..."}] OR list[{"id": "..."}] OR list[str]
    """
    for key in ["doc_ids", "document_ids", "ids"]:
        if key in resp_json and isinstance(resp_json[key], list):
            return [str(x) for x in resp_json[key]]

    if "retrieved" in resp_json and isinstance(resp_json["retrieved"], list):
        out = []
        for x in resp_json["retrieved"]:
            if isinstance(x, dict):
                if "doc_id" in x:
                    out.append(str(x["doc_id"]))
                elif "id" in x:
                    out.append(str(x["id"]))
            else:
                out.append(str(x))
        return out

    if "sources" in resp_json and isinstance(resp_json["sources"], list):
        out = []
        for s in resp_json["sources"]:
            if isinstance(s, dict):
                if "doc_id" in s:
                    out.append(str(s["doc_id"]))
                elif "id" in s:
                    out.append(str(s["id"]))
                elif "source_id" in s:
                    out.append(str(s["source_id"]))
            else:
                out.append(str(s))
        return out

    # If your endpoint returns citations in a different shape, change this function.
    return []


def extract_answer_and_sources(resp_json: Dict[str, Any]) -> Tuple[str, str, bool, str]:
    """
    For grounding eval export.
    We store answer + a compact sources string.
    Adjust if your API uses different fields.
    """
    answer = ""
    for k in ["answer", "output", "response", "text"]:
        if k in resp_json and isinstance(resp_json[k], str):
            answer = resp_json[k]
            break

    sources = ""
    if "sources" in resp_json:
        sources = json.dumps(resp_json["sources"], ensure_ascii=False)
    elif "citations" in resp_json:
        sources = json.dumps(resp_json["citations"], ensure_ascii=False)

    refusal_obj = resp_json.get("refusal") or {}
    is_refusal = bool(refusal_obj.get("is_refusal", False))
    refusal_reason = str(refusal_obj.get("reason", "")).strip()

    return answer, sources, is_refusal, refusal_reason


# ----------------------------
# Eval dataset IO
# ----------------------------
def load_eval_jsonl(path: str) -> List[Dict[str, Any]]:
    """
    Each line must contain:
      {"query": "...", "relevant_doc_ids": ["doc1","doc2",...]}
    """
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if "query" not in item or "relevant_doc_ids" not in item:
                raise ValueError("Each JSONL line must include 'query' and 'relevant_doc_ids'.")
            data.append(item)
    return data


# ----------------------------
# Retrieval evaluation (BM25 vs Hybrid)
# ----------------------------
async def evaluate_retrieval(
    eval_data: List[Dict[str, Any]],
    hybrid_url: str,
    bm25_url: str,
    method: str,
    payload_template: Dict[str, Any],
    k: int,
    timeout_s: float,
    concurrency: int,
) -> Dict[str, Any]:
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        async def one(item: Dict[str, Any]) -> Tuple[float, float, float, float]:
            q = item["query"]
            rel = [str(x) for x in item["relevant_doc_ids"]]

            async with sem:
                h = await call_retriever(client, hybrid_url, method, payload_template, q, timeout_s)
            async with sem:
                b = await call_retriever(client, bm25_url, method, payload_template, q, timeout_s)

            h_ids = extract_doc_ids(h)
            b_ids = extract_doc_ids(b)

            hp = precision_at_k(h_ids, rel, k)
            hr = recall_at_k(h_ids, rel, k)
            bp = precision_at_k(b_ids, rel, k)
            br = recall_at_k(b_ids, rel, k)
            return hp, hr, bp, br

        tasks = [asyncio.create_task(one(item)) for item in eval_data]
        rows = await asyncio.gather(*tasks)

    hps = [r[0] for r in rows]
    hrs = [r[1] for r in rows]
    bps = [r[2] for r in rows]
    brs = [r[3] for r in rows]

    out = {
        "k": k,
        "hybrid_precision_at_k": float(np.mean(hps)),
        "hybrid_recall_at_k": float(np.mean(hrs)),
        "bm25_precision_at_k": float(np.mean(bps)),
        "bm25_recall_at_k": float(np.mean(brs)),
    }
    out["precision_improvement_percent"] = pct_improvement(out["hybrid_precision_at_k"], out["bm25_precision_at_k"])
    out["recall_improvement_percent"] = pct_improvement(out["hybrid_recall_at_k"], out["bm25_recall_at_k"])
    return out


# ----------------------------
# Grounding eval export + scoring
# ----------------------------
async def export_grounding_sheet(
    queries_path: str,
    out_csv: str,
    query_url: str,
    method: str,
    payload_template: Dict[str, Any],
    timeout_s: float,
    concurrency: int,
) -> None:
    with open(queries_path, "r", encoding="utf-8") as f:
        queries = [line.strip() for line in f if line.strip()]

    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        async def one(q: str) -> Dict[str, Any]:
            try:
                async with sem:
                    resp = await call_retriever(
                        client, query_url, method, payload_template, q, timeout_s
                    )
                ans, src, is_refusal, refusal_reason = extract_answer_and_sources(resp)
                return {
                    "query": q,
                    "answer": ans,
                    "sources": src,
                    "is_refusal_model": "1" if is_refusal else "0",
                    "refusal_reason": refusal_reason,
                }
            except Exception as e:
                # Keep export resilient: one timeout/error should not abort all rows.
                return {
                    "query": q,
                    "answer": "",
                    "sources": f"ERROR: {str(e)}",
                    "is_refusal_model": "1",
                    "refusal_reason": f"request_error: {str(e)}",
                }

        rows = await asyncio.gather(*[asyncio.create_task(one(q)) for q in queries])

    # Create CSV with a column you fill manually: is_grounded (1/0)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "query",
                "answer",
                "sources",
                "is_refusal_model",
                "refusal_reason",
                "is_grounded",
            ],
        )
        w.writeheader()
        for r in rows:
            r["is_grounded"] = ""  # fill with 1 or 0 manually
            w.writerow(r)

    print(f"Grounding sheet exported: {out_csv}")
    print("Now open the CSV, label is_grounded with 1 (grounded) or 0 (hallucinated), then run: --mode grounding-score")


def score_grounding_csv(labeled_csv: str) -> Dict[str, Any]:
    total = 0
    quality_rows = 0
    request_error_rows = 0
    grounded = 0
    missing = 0
    refusal_rows = 0

    with open(labeled_csv, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            total += 1
            sources = (row.get("sources") or "").strip().lower()
            refusal_reason = (row.get("refusal_reason") or "").strip().lower()
            is_request_error = ("error:" in sources) or (
                refusal_reason.startswith("request_error:")
            )
            if is_request_error:
                request_error_rows += 1
                continue

            quality_rows += 1
            answer = (row.get("answer") or "").strip().lower()
            ref_flag = (row.get("is_refusal_model") or "").strip().lower()
            if ref_flag in {"1", "true", "yes"} or (
                "not available in the provided documents" in answer
                or "i cannot answer" in answer
            ):
                refusal_rows += 1
            val = (row.get("is_grounded") or "").strip()
            if val == "":
                missing += 1
                continue
            if val not in {"0", "1"}:
                raise ValueError("is_grounded must be 1 or 0 (or blank).")
            if val == "1":
                grounded += 1

    labeled = quality_rows - missing
    grounded_rate = grounded / labeled if labeled > 0 else 0.0
    hallucination_rate = 1.0 - grounded_rate if labeled > 0 else 0.0
    refusal_rate = refusal_rows / quality_rows if quality_rows > 0 else 0.0
    non_refusal_rows = max(0, quality_rows - refusal_rows)
    answered_grounded_rate = (
        grounded / non_refusal_rows if non_refusal_rows > 0 else 0.0
    )

    return {
        "total_rows": total,
        "quality_rows": quality_rows,
        "request_error_rows": request_error_rows,
        "labeled_rows": labeled,
        "missing_labels": missing,
        "grounded_rate": grounded_rate,
        "hallucination_rate": hallucination_rate,
        "refusal_rows": refusal_rows,
        "refusal_rate": refusal_rate,
        "answered_grounded_rate": answered_grounded_rate,
    }


def auto_label_grounding_csv(csv_path: str) -> Dict[str, Any]:
    """
    Auto-label blank is_grounded rows with a strict heuristic:
    - 0 if sources empty/error, or answer empty, or refusal-style fallback answer
    - 1 otherwise
    """
    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fields = r.fieldnames or [
            "query",
            "answer",
            "sources",
            "is_refusal_model",
            "refusal_reason",
            "is_grounded",
        ]
        for row in r:
            rows.append(row)

    updated = 0
    kept = 0
    skipped_request_errors = 0
    grounded = 0
    hallucinated = 0

    for row in rows:
        sources = (row.get("sources") or "").strip().lower()
        refusal_reason = (row.get("refusal_reason") or "").strip().lower()
        is_request_error = ("error:" in sources) or (
            refusal_reason.startswith("request_error:")
        )
        if is_request_error:
            # Keep these unlabeled; they are connectivity failures, not model quality.
            row["is_grounded"] = ""
            skipped_request_errors += 1
            continue

        cur = (row.get("is_grounded") or "").strip()
        if cur in {"0", "1"}:
            kept += 1
            if cur == "1":
                grounded += 1
            else:
                hallucinated += 1
            continue

        answer = (row.get("answer") or "").strip().lower()
        sources = (row.get("sources") or "").strip().lower()
        ref_flag = (row.get("is_refusal_model") or "").strip().lower()
        label = "1"
        if ref_flag in {"1", "true", "yes"}:
            label = "1"
        if not answer:
            label = "0"
        if "error:" in sources:
            label = "0"
        if "i found relevant sources, but i could not produce a reliable final answer" in answer:
            label = "0"
        if "i cannot answer" in answer:
            label = "0"
        if sources in {"", "[]"}:
            label = "0"

        row["is_grounded"] = label
        updated += 1
        if label == "1":
            grounded += 1
        else:
            hallucinated += 1

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "query",
                "answer",
                "sources",
                "is_refusal_model",
                "refusal_reason",
                "is_grounded",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    return {
        "rows_total": len(rows),
        "rows_updated": updated,
        "rows_kept_labeled": kept,
        "rows_skipped_request_errors": skipped_request_errors,
        "grounded_1": grounded,
        "hallucinated_0": hallucinated,
        "path": csv_path,
    }


# ----------------------------
# Stability test (duration-based)
# ----------------------------
@dataclass
class ReqResult:
    ok: bool
    latency_ms: float


async def stability_test(
    url: str,
    method: str,
    payload_template: Dict[str, Any],
    query: str,
    duration_minutes: int,
    concurrency: int,
    timeout_s: float,
    out_csv: str,
) -> Dict[str, Any]:
    stop_at = time.time() + duration_minutes * 60
    sem = asyncio.Semaphore(concurrency)

    # time-bucket stats per minute
    buckets: Dict[int, List[ReqResult]] = {}

    async with httpx.AsyncClient() as client:
        async def one_loop(worker_id: int) -> None:
            del worker_id
            while time.time() < stop_at:
                async with sem:
                    start = time.perf_counter()
                    ok = True
                    try:
                        payload = dict(payload_template)
                        payload["query"] = query
                        if method.upper() == "GET":
                            resp = await client.get(url, params=payload, timeout=timeout_s)
                        else:
                            resp = await client.request(method.upper(), url, json=payload, timeout=timeout_s)
                        ok = 200 <= resp.status_code < 300
                    except Exception:
                        ok = False
                    latency_ms = (time.perf_counter() - start) * 1000.0

                minute_idx = int((time.time() - (stop_at - duration_minutes * 60)) // 60)
                buckets.setdefault(minute_idx, []).append(ReqResult(ok=ok, latency_ms=latency_ms))

        tasks = [asyncio.create_task(one_loop(i)) for i in range(concurrency)]
        await asyncio.gather(*tasks)

    # Write per-minute CSV
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["minute", "requests", "rps", "error_rate_percent", "lat_avg_ms", "lat_p95_ms", "lat_p99_ms"],
        )
        w.writeheader()

        all_lat = []
        all_ok = 0
        all_total = 0

        for minute in sorted(buckets.keys()):
            arr = buckets[minute]
            total = len(arr)
            oks = sum(1 for x in arr if x.ok)
            fails = total - oks
            lats = [x.latency_ms for x in arr]
            all_lat.extend(lats)
            all_ok += oks
            all_total += total

            w.writerow(
                {
                    "minute": minute,
                    "requests": total,
                    "rps": total / 60.0,
                    "error_rate_percent": (fails / total * 100.0) if total else 0.0,
                    "lat_avg_ms": float(np.mean(lats)) if lats else float("nan"),
                    "lat_p95_ms": p(lats, 95),
                    "lat_p99_ms": p(lats, 99),
                }
            )

    # Overall summary
    error_rate = ((all_total - all_ok) / all_total * 100.0) if all_total else 0.0
    summary = {
        "duration_minutes": duration_minutes,
        "total_requests": all_total,
        "throughput_rps_overall": (all_total / (duration_minutes * 60.0)) if duration_minutes > 0 else 0.0,
        "error_rate_percent": error_rate,
        "latency_avg_ms": float(np.mean(all_lat)) if all_lat else float("nan"),
        "latency_p95_ms": p(all_lat, 95),
        "latency_p99_ms": p(all_lat, 99),
        "per_minute_csv": out_csv,
    }
    return summary


# ----------------------------
# Main CLI
# ----------------------------
def parse_payload(payload_str: str) -> Dict[str, Any]:
    if not payload_str:
        return {}
    return cast(Dict[str, Any], json.loads(payload_str))


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure production-grade metrics for RAG/ML systems.")
    ap.add_argument("--mode", required=True,
                    choices=["corpus", "retrieval-eval", "grounding-export", "grounding-autolabel", "grounding-score", "stability"],
                    help="What to measure")

    # corpus
    ap.add_argument("--faiss_index", default=None, help="Path to FAISS index file (e.g., index.faiss)")
    ap.add_argument("--chroma_dir", default=None, help="Path to Chroma persist directory")
    ap.add_argument("--chroma_collection", default=None, help="Chroma collection name")

    # endpoints
    ap.add_argument("--hybrid_url", default=None, help="Hybrid retriever endpoint URL")
    ap.add_argument("--bm25_url", default=None, help="BM25-only retriever endpoint URL (required for retrieval-eval)")
    ap.add_argument("--query_url", default=None, help="Main query endpoint URL (for grounding/stability)")
    ap.add_argument("--method", default="POST", help="HTTP method (POST/GET)")
    ap.add_argument("--payload", default="{}", help="JSON payload template (must NOT include query)")
    ap.add_argument("--timeout", type=float, default=10.0)

    # retrieval eval
    ap.add_argument("--eval_jsonl", default=None, help="Path to eval JSONL with query + relevant_doc_ids")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=20)

    # grounding
    ap.add_argument("--grounding_queries", default=None, help="Text file: 1 query per line (100 lines recommended)")
    ap.add_argument("--out_csv", default="output.csv", help="Output CSV path")

    # stability
    ap.add_argument("--duration_minutes", type=int, default=10)
    ap.add_argument("--stability_query", default="health check", help="Query to send repeatedly")

    args = ap.parse_args()
    payload_template = parse_payload(args.payload)

    if args.mode == "corpus":
        if args.faiss_index:
            ntotal = get_faiss_ntotal(args.faiss_index)
            print(json.dumps({"faiss_index": args.faiss_index, "chunk_vectors": ntotal}, indent=2))
        if args.chroma_dir and args.chroma_collection:
            chunks, docs = get_chroma_count(args.chroma_dir, args.chroma_collection)
            print(json.dumps({"chroma_dir": args.chroma_dir, "collection": args.chroma_collection,
                              "chunks": chunks, "docs_estimate": docs}, indent=2))
        if not args.faiss_index and not (args.chroma_dir and args.chroma_collection):
            raise SystemExit("Provide --faiss_index OR (--chroma_dir AND --chroma_collection).")

    elif args.mode == "retrieval-eval":
        if not (args.eval_jsonl and args.hybrid_url and args.bm25_url):
            raise SystemExit("Need --eval_jsonl --hybrid_url --bm25_url")
        eval_data = load_eval_jsonl(args.eval_jsonl)
        out = asyncio.run(
            evaluate_retrieval(
                eval_data=eval_data,
                hybrid_url=args.hybrid_url,
                bm25_url=args.bm25_url,
                method=args.method,
                payload_template=payload_template,
                k=args.k,
                timeout_s=args.timeout,
                concurrency=args.concurrency,
            )
        )
        print(json.dumps(out, indent=2))

    elif args.mode == "grounding-export":
        if not (args.grounding_queries and args.query_url):
            raise SystemExit("Need --grounding_queries and --query_url")
        asyncio.run(
            export_grounding_sheet(
                queries_path=args.grounding_queries,
                out_csv=args.out_csv,
                query_url=args.query_url,
                method=args.method,
                payload_template=payload_template,
                timeout_s=args.timeout,
                concurrency=args.concurrency,
            )
        )

    elif args.mode == "grounding-score":
        if not os.path.exists(args.out_csv):
            raise SystemExit(f"CSV not found: {args.out_csv}")
        out = score_grounding_csv(args.out_csv)
        print(json.dumps(out, indent=2))

    elif args.mode == "grounding-autolabel":
        if not os.path.exists(args.out_csv):
            raise SystemExit(f"CSV not found: {args.out_csv}")
        out = auto_label_grounding_csv(args.out_csv)
        print(json.dumps(out, indent=2))

    elif args.mode == "stability":
        if not args.query_url:
            raise SystemExit("Need --query_url")
        out = asyncio.run(
            stability_test(
                url=args.query_url,
                method=args.method,
                payload_template=payload_template,
                query=args.stability_query,
                duration_minutes=args.duration_minutes,
                concurrency=args.concurrency,
                timeout_s=args.timeout,
                out_csv=args.out_csv,
            )
        )
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
