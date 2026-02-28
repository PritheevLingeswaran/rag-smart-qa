from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from api.deps import get_answerer, get_retriever, get_settings
from evaluation.confidence_calibration import expected_calibration_error
from evaluation.cost_analysis import summarize_cost
from evaluation.hallucination import heuristic_grounded, llm_judge_grounded
from evaluation.metrics import exact_match, token_f1
from evaluation.performance import summarize_latency
from evaluation.retrieval_metrics import (
    compare_hybrid_vs_dense,
    hurt_precision_case,
    improved_recall_case,
)
from retrieval.corpus import load_chunks_jsonl
from utils.openai_client import OpenAIClient


@dataclass
class Example:
    id: str
    question: str
    answer: str
    relevant_chunk_ids: set[str]


def _load_dataset(path: str) -> list[Example]:
    exs: list[Example] = []
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            exs.append(
                Example(
                    id=str(obj["id"]),
                    question=str(obj["question"]),
                    answer=str(obj["answer"]),
                    relevant_chunk_ids=set(obj.get("relevant_chunk_ids", []) or []),
                )
            )
    return exs


def evaluate_main() -> None:
    settings = get_settings()
    retriever = get_retriever()
    answerer = get_answerer()

    dataset = _load_dataset(settings.evaluation.dataset_path)
    k = settings.vector_store.top_k

    # Retrieval metrics (dense vs hybrid). We always compute both when possible.
    dense_p_at_k: list[float] = []
    dense_r_at_k: list[float] = []
    dense_mrrs: list[float] = []

    hybrid_p_at_k: list[float] = []
    hybrid_r_at_k: list[float] = []
    hybrid_mrrs: list[float] = []

    improved_recall_ids: list[str] = []
    hurt_precision_ids: list[str] = []
    improved_recall_samples: list[str] = []
    hurt_precision_samples: list[str] = []
    ems: list[int] = []
    f1s: list[float] = []
    hallucinated: list[int] = []
    confs: list[float] = []
    costs: list[float] = []

    # Latency measurements (seconds)
    retrieval_lat_s: list[float] = []
    generation_lat_s: list[float] = []
    e2e_lat_s: list[float] = []

    # Corpus stats (chunk count / sources). This helps quantify scale.
    corpus_chunks = 0
    corpus_sources = 0
    try:
        chunks_path = str(Path(settings.paths.chunks_dir) / "chunks.jsonl")
        chunks, _ = load_chunks_jsonl(chunks_path)
        corpus_chunks = len(chunks)
        corpus_sources = len({c.source for c in chunks})
    except Exception:
        # If the user runs eval before ingest, keep the report usable.
        corpus_chunks = 0
        corpus_sources = 0

    judge_client = None
    if settings.evaluation.enable_llm_judge:
        oai = settings.embeddings.openai
        judge_client = OpenAIClient(
            api_key=oai.api_key,
            base_url=oai.base_url,
            organization=oai.organization,
            timeout_s=oai.request_timeout_s,
            max_retries=oai.max_retries,
        )

    for ex in dataset:
        # For a clean dense-vs-hybrid comparison, we disable query rewriting.
        t0 = time.perf_counter()
        r_dense = retriever.retrieve(
            ex.question, top_k=k, rewrite_override=False, mode_override="dense"
        )
        dense_lat = time.perf_counter() - t0

        t1 = time.perf_counter()
        r_hybrid = retriever.retrieve(
            ex.question, top_k=k, rewrite_override=False, mode_override="hybrid"
        )
        hybrid_lat = time.perf_counter() - t1

        dense_ids = [h.chunk.chunk_id for h in r_dense.hits]
        hybrid_ids = [h.chunk.chunk_id for h in r_hybrid.hits]

        if ex.relevant_chunk_ids:
            cmp = compare_hybrid_vs_dense(
                dense_retrieved=dense_ids,
                hybrid_retrieved=hybrid_ids,
                relevant=ex.relevant_chunk_ids,
                k=k,
            )

            dense_p_at_k.append(cmp.dense.precision)
            dense_r_at_k.append(cmp.dense.recall)
            dense_mrrs.append(cmp.dense.mrr)

            hybrid_p_at_k.append(cmp.hybrid.precision)
            hybrid_r_at_k.append(cmp.hybrid.recall)
            hybrid_mrrs.append(cmp.hybrid.mrr)

            if improved_recall_case(cmp):
                improved_recall_ids.append(ex.id)
                if len(improved_recall_samples) < 5:
                    improved_recall_samples.append(f"{ex.id}: {ex.question}")
            if hurt_precision_case(cmp):
                hurt_precision_ids.append(ex.id)
                if len(hurt_precision_samples) < 5:
                    hurt_precision_samples.append(f"{ex.id}: {ex.question}")

        # Use the system's configured mode for generation metrics.
        if settings.retrieval.hybrid.enabled:
            r = r_hybrid
            selected_retrieval_lat = hybrid_lat
        else:
            r = r_dense
            selected_retrieval_lat = dense_lat

        tg0 = time.perf_counter()
        g = answerer.generate(ex.question, r.hits)
        gen_lat = time.perf_counter() - tg0

        retrieval_lat_s.append(selected_retrieval_lat)
        generation_lat_s.append(gen_lat)
        e2e_lat_s.append(selected_retrieval_lat + gen_lat)

        em = 1 if exact_match(g.answer, ex.answer) else 0
        ems.append(em)
        f1s.append(token_f1(g.answer, ex.answer))
        confs.append(g.confidence)
        costs.append(float(r.embedding_cost_usd + g.llm_cost_usd))

        src_texts = [h.chunk.text for h in r.hits]
        grounded = heuristic_grounded(g.answer, src_texts)
        if judge_client is not None:
            grounded = llm_judge_grounded(
                judge_client, settings.evaluation.judge_model, ex.question, g.answer, src_texts
            )
        hallucinated.append(0 if grounded or g.refusal.is_refusal else 1)

    if dense_p_at_k and hybrid_p_at_k:
        dense_block = (
            f"- dense precision@{k}: {sum(dense_p_at_k) / len(dense_p_at_k):.3f}\n"
            f"- dense recall@{k}: {sum(dense_r_at_k) / len(dense_r_at_k):.3f}\n"
            f"- dense MRR: {sum(dense_mrrs) / len(dense_mrrs):.3f}\n"
        )
        hybrid_block = (
            f"- hybrid precision@{k}: {sum(hybrid_p_at_k) / len(hybrid_p_at_k):.3f}\n"
            f"- hybrid recall@{k}: {sum(hybrid_r_at_k) / len(hybrid_r_at_k):.3f}\n"
            f"- hybrid MRR: {sum(hybrid_mrrs) / len(hybrid_mrrs):.3f}\n"
        )
        delta_block = (
            f"- Δprecision@{k}: {(sum(hybrid_p_at_k) / len(hybrid_p_at_k)) - (sum(dense_p_at_k) / len(dense_p_at_k)):+.3f}\n"
            f"- Δrecall@{k}: {(sum(hybrid_r_at_k) / len(hybrid_r_at_k)) - (sum(dense_r_at_k) / len(dense_r_at_k)):+.3f}\n"
        )
        case_block = (
            f"- examples with improved recall: {len(improved_recall_ids)}\n"
            f"- examples with hurt precision: {len(hurt_precision_ids)}\n"
            f"- sample improved recall (id: question): {improved_recall_samples}\n"
            f"- sample hurt precision (id: question): {hurt_precision_samples}\n"
        )
        retrieval_block = dense_block + "\n" + hybrid_block + "\n" + delta_block + "\n" + case_block
    else:
        retrieval_block = "- (no relevant_chunk_ids provided; retrieval metrics skipped)\n"

    avg_em = sum(ems) / max(1, len(ems))
    avg_f1 = sum(f1s) / max(1, len(f1s))
    hall_rate = sum(hallucinated) / max(1, len(hallucinated))
    ece, _ = expected_calibration_error(confs, ems, n_bins=10)
    cost_stats = summarize_cost(costs)

    ret_lat = summarize_latency(retrieval_lat_s)
    gen_lat = summarize_latency(generation_lat_s)
    e2e_lat = summarize_latency(e2e_lat_s)

    load_block = "- (run scripts/load_test.py to generate load test results)\n"
    load_json = Path("docs/load_test_results.json")
    if load_json.exists():
        try:
            obj = json.loads(load_json.read_text(encoding="utf-8"))
            load_block = (
                f"- concurrency: {obj.get('concurrency')}\n"
                f"- total_requests: {obj.get('total_requests')}\n"
                f"- throughput_rps: {obj.get('throughput_rps'):.2f}\n"
                f"- success_rate: {obj.get('success_rate'):.3f}\n"
                f"- p95_latency_ms: {obj.get('p95_latency_ms'):.2f}\n"
            )
        except Exception:
            load_block = "- (load test results found but could not be parsed)\n"

    out = (
        "# Evaluation Results\n\n"
        f"Dataset: `{settings.evaluation.dataset_path}`\n\n"
        "## Corpus Size\n"
        f"- chunks: {corpus_chunks}\n"
        f"- unique sources: {corpus_sources}\n\n"
        "## Retrieval\n"
        f"{retrieval_block}\n"
        "## Answer Quality\n"
        f"- exact match: {avg_em:.3f}\n"
        f"- token F1: {avg_f1:.3f}\n\n"
        "## Hallucination\n"
        f"- hallucination rate: {hall_rate:.3f}\n\n"
        "## Latency (local eval run)\n"
        f"- retrieval p95 (ms): {ret_lat.p95_ms:.2f}\n"
        f"- generation p95 (ms): {gen_lat.p95_ms:.2f}\n"
        f"- end-to-end p95 (ms): {e2e_lat.p95_ms:.2f}\n"
        f"- end-to-end avg (ms): {e2e_lat.avg_ms:.2f}\n\n"
        "## Confidence Calibration\n"
        f"- ECE: {ece:.3f}\n\n"
        "## Cost\n"
        f"- avg cost/query (USD): {cost_stats.avg_cost_usd:.6f}\n"
        f"- p95 cost/query (USD): {cost_stats.p95_cost_usd:.6f}\n"
        f"- total cost (USD): {cost_stats.total_cost_usd:.6f}\n"
        "\n## Load-handling capability (HTTP load test)\n"
        f"{load_block}"
    )

    Path("docs/evaluation_results.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    evaluate_main()
