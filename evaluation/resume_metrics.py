from __future__ import annotations

import asyncio
import json
import os
import re
import socket
import subprocess
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import httpx

from evaluation.performance import LatencyStats, summarize_latency
from evaluation.retrieval_metrics import mrr, precision_at_k, recall_at_k
from generation.answerer import Answerer
from retrieval.retriever import Retriever
from retrieval.vector_store import ChromaVectorStore, FaissVectorStore, build_vector_store
from utils.settings import Settings

RetrievalMode = Literal["dense", "hybrid", "bm25"]


@dataclass(frozen=True)
class RetrievalExample:
    id: str
    query: str
    relevant_chunk_ids: set[str]


@dataclass(frozen=True)
class HallucinationExample:
    id: str
    question: str
    expected_behavior: Literal["answer", "refuse"]
    acceptable_answers: list[str]
    notes: str = ""


@dataclass(frozen=True)
class LoadTestRow:
    concurrency: int
    total_requests: int
    success_count: int
    failure_count: int
    failure_rate: float
    avg_latency_ms: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    measured: bool = True
    sample_errors: list[str] | None = None
    wall_time_s: float | None = None


def load_retrieval_examples(path: str) -> list[RetrievalExample]:
    rows: list[RetrievalExample] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            rows.append(
                RetrievalExample(
                    id=str(obj["id"]),
                    query=str(obj["query"]),
                    relevant_chunk_ids={str(v) for v in obj["relevant_chunk_ids"]},
                )
            )
    return rows


def load_hallucination_examples(path: str) -> list[HallucinationExample]:
    rows: list[HallucinationExample] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            expected_behavior = str(obj["expected_behavior"])
            if expected_behavior not in {"answer", "refuse"}:
                raise ValueError(f"Invalid expected_behavior={expected_behavior!r} in {path}")
            rows.append(
                HallucinationExample(
                    id=str(obj["id"]),
                    question=str(obj["question"]),
                    expected_behavior=cast(Literal["answer", "refuse"], expected_behavior),
                    acceptable_answers=[str(v) for v in obj.get("acceptable_answers", [])],
                    notes=str(obj.get("notes", "")),
                )
            )
    return rows


def validate_retrieval_examples(examples: list[RetrievalExample]) -> dict[str, Any]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for item in examples:
        if not item.id or item.id in seen_ids:
            errors.append(f"Invalid or duplicate retrieval id: {item.id!r}")
        seen_ids.add(item.id)
        if not item.query.strip():
            errors.append(f"Empty retrieval query for id={item.id}")
        if not item.relevant_chunk_ids:
            errors.append(f"Missing relevant_chunk_ids for id={item.id}")
    return {
        "valid": not errors,
        "example_count": len(examples),
        "errors": errors,
    }


def validate_hallucination_examples(examples: list[HallucinationExample]) -> dict[str, Any]:
    errors: list[str] = []
    label_counts = {"answer": 0, "refuse": 0}
    seen_ids: set[str] = set()
    for item in examples:
        if not item.id or item.id in seen_ids:
            errors.append(f"Invalid or duplicate hallucination id: {item.id!r}")
        seen_ids.add(item.id)
        label_counts[item.expected_behavior] = label_counts.get(item.expected_behavior, 0) + 1
        if not item.question.strip():
            errors.append(f"Empty hallucination question for id={item.id}")
        if item.expected_behavior == "answer" and not item.acceptable_answers:
            errors.append(f"Missing acceptable_answers for answerable example id={item.id}")
    return {
        "valid": not errors,
        "example_count": len(examples),
        "label_counts": label_counts,
        "errors": errors,
    }


def normalize_answer(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"\(source:[^)]+\)", "", text, flags=re.IGNORECASE)
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def answer_matches(answer: str, acceptable_answers: list[str]) -> bool:
    if not acceptable_answers:
        return True
    normalized = normalize_answer(answer)
    return any(normalized == normalize_answer(candidate) for candidate in acceptable_answers)


def has_valid_citation(answer: str, source_ids: list[str]) -> bool:
    citations = re.findall(r"\[([^\]]+)\]", answer)
    if not citations:
        return False
    valid = set(source_ids)
    return all(citation in valid for citation in citations)


def file_size_bytes(path: Path) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    return int(path.stat().st_size)


def directory_size_bytes(path: Path) -> int | None:
    if not path.exists():
        return None
    if path.is_file():
        return int(path.stat().st_size)
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += int(child.stat().st_size)
    return total


def summarize_dataset_stats(settings: Settings) -> dict[str, Any]:
    chunks_path = Path(settings.paths.chunks_dir) / "chunks.jsonl"
    unique_sources: set[str] = set()
    chunk_count = 0
    if chunks_path.exists():
        with chunks_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                obj = json.loads(line)
                chunk_count += 1
                unique_sources.add(str(obj.get("source", "")))

    raw_documents = sorted(Path(settings.paths.raw_dir).glob("*"))
    vector_store = build_vector_store(settings)
    vector_count = 0
    if isinstance(vector_store, ChromaVectorStore):
        vector_count = int(vector_store._collection.count())
    elif isinstance(vector_store, FaissVectorStore) and vector_store.index is not None:
        vector_count = int(vector_store.index.ntotal)

    vector_index_path = (
        Path(settings.vector_store.chroma.persist_dir)
        if settings.vector_store.provider == "chroma"
        else Path(settings.paths.indexes_dir) / "faiss"
    )
    bm25_path = Path(settings.paths.indexes_dir) / "bm25"

    return {
        "measured": True,
        "documents_indexed": len(unique_sources),
        "chunks_indexed": chunk_count,
        "vectors_indexed": vector_count,
        "raw_documents_present": len(raw_documents),
        "index_sizes_bytes": {
            "vector_index": directory_size_bytes(vector_index_path),
            "bm25_index": directory_size_bytes(bm25_path),
            "chunks_file": file_size_bytes(chunks_path),
        },
        "paths": {
            "chunks": str(chunks_path),
            "vector_index": str(vector_index_path),
            "bm25_index": str(bm25_path),
        },
        "limitations": (
            "Measured corpus size is limited by the files currently present under data/raw/documents."
        ),
    }


def make_eval_settings(base: Settings) -> Settings:
    settings = base.model_copy(deep=True)
    settings.retrieval.query_rewrite.enabled = False
    settings.api.reload = False
    return settings


def make_dense_settings(base: Settings) -> Settings:
    settings = make_eval_settings(base)
    settings.retrieval.hybrid.enabled = False
    settings.retrieval.rerank.enabled = False
    return settings


def make_hybrid_settings(
    base: Settings,
    *,
    fusion_method: Literal["weighted", "rrf"],
    rerank_enabled: bool | None = None,
) -> Settings:
    settings = make_eval_settings(base)
    settings.retrieval.hybrid.enabled = True
    settings.retrieval.hybrid.fusion_method = fusion_method
    if rerank_enabled is not None:
        settings.retrieval.rerank.enabled = rerank_enabled
    return settings


def make_baseline_answerer_settings(base: Settings) -> Settings:
    settings = make_dense_settings(base)
    settings.generation.strict_refusal = False
    settings.generation.answerability.partial_top_score = 0.0
    settings.generation.answerability.answerable_top_score = 0.0
    settings.generation.answerability.evidence_score_threshold = 0.0
    return settings


def make_strict_hybrid_answerer_settings(base: Settings) -> Settings:
    settings = make_hybrid_settings(base, fusion_method="rrf")
    settings.generation.strict_refusal = True
    return settings


def make_answerer(settings: Settings) -> Answerer:
    answerer = Answerer(settings)
    if not settings.embeddings.openai.api_key:
        answerer._disable_remote_generation = True
    return answerer


def latency_stats_dict(stats: LatencyStats) -> dict[str, float | int]:
    return {
        "n": stats.n,
        "avg_latency_ms": round(stats.avg_ms, 3),
        "p50_latency_ms": round(stats.p50_ms, 3),
        "p95_latency_ms": round(stats.p95_ms, 3),
        "p99_latency_ms": round(stats.p99_ms, 3),
    }


def benchmark_retrieval_latency(
    retriever: Retriever,
    examples: list[RetrievalExample],
    *,
    mode: RetrievalMode,
    label: str,
    top_k: int,
) -> dict[str, Any]:
    latencies_s: list[float] = []
    per_query: list[dict[str, Any]] = []
    if examples:
        retriever.retrieve(
            examples[0].query,
            top_k=top_k,
            rewrite_override=False,
            mode_override=mode,
        )
    for example in examples:
        started = time.perf_counter()
        result = retriever.retrieve(
            example.query,
            top_k=top_k,
            rewrite_override=False,
            mode_override=mode,
        )
        elapsed_s = time.perf_counter() - started
        latencies_s.append(elapsed_s)
        per_query.append(
            {
                "id": example.id,
                "query": example.query,
                "latency_ms": round(elapsed_s * 1000.0, 3),
                "query_used": result.query_used,
                "num_hits": len(result.hits),
            }
        )

    stats = summarize_latency(latencies_s)
    return {
        "measured": True,
        "label": label,
        "mode": mode,
        "query_count": len(examples),
        "top_k": top_k,
        "summary": latency_stats_dict(stats),
        "per_query": per_query,
    }


def _first_relevant_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> int | None:
    for idx, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return idx
    return None


def _hit_rate(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    return 1.0 if recall_at_k(retrieved_ids, relevant_ids, k) > 0 else 0.0


def _choose_default_variant(report: dict[str, Any]) -> str:
    candidates = []
    for name, metrics in report["modes"].items():
        k1 = metrics["summary_by_k"].get("1", {})
        k5 = metrics["summary_by_k"].get("5", {})
        score = (
            float(k1.get("precision", 0.0)) * 3.0
            + float(k5.get("recall", 0.0)) * 2.0
            + float(metrics.get("mrr", 0.0))
        )
        candidates.append((score, name))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else "dense"


def _variant_mode(name: str) -> RetrievalMode:
    return "dense" if name == "dense" else "hybrid"


def evaluate_retrieval_variants(
    retrievers: dict[str, Retriever],
    examples: list[RetrievalExample],
    *,
    top_ks: list[int],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    max_k = max(top_ks)
    raw_results: dict[str, dict[str, list[str]]] = {name: {} for name in retrievers}
    diagnostics: list[dict[str, Any]] = []

    for example in examples:
        example_diag: dict[str, Any] = {
            "id": example.id,
            "query": example.query,
            "relevant_doc_ids": sorted(example.relevant_chunk_ids),
            "variants": {},
        }
        for name, retriever in retrievers.items():
            result = retriever.retrieve_with_debug(
                example.query,
                top_k=max_k,
                rewrite_override=False,
                mode_override=_variant_mode(name),
            )
            ids = [hit.chunk.chunk_id for hit in result.hits]
            raw_results[name][example.id] = ids
            first_rank = _first_relevant_rank(ids, example.relevant_chunk_ids)
            example_diag["variants"][name] = {
                "retrieved_doc_ids": ids,
                "first_relevant_rank": first_rank,
                "debug": result.debug,
            }
        dense_rank = example_diag["variants"]["dense"]["first_relevant_rank"]
        for name, payload in example_diag["variants"].items():
            if name == "dense":
                payload["first_relevant_moved"] = "baseline"
                continue
            rank = payload["first_relevant_rank"]
            if dense_rank is None and rank is not None:
                payload["first_relevant_moved"] = "up"
            elif dense_rank is not None and rank is None:
                payload["first_relevant_moved"] = "down"
            elif dense_rank is None and rank is None:
                payload["first_relevant_moved"] = "unchanged"
            elif rank < dense_rank:
                payload["first_relevant_moved"] = "up"
            elif rank > dense_rank:
                payload["first_relevant_moved"] = "down"
            else:
                payload["first_relevant_moved"] = "unchanged"
        diagnostics.append(example_diag)

    modes: dict[str, Any] = {}
    for name in retrievers:
        summary_by_k: dict[str, dict[str, float]] = {}
        mrr_values: list[float] = []
        for k in top_ks:
            precisions: list[float] = []
            recalls: list[float] = []
            hit_rates: list[float] = []
            for example in examples:
                retrieved_ids = raw_results[name][example.id]
                precisions.append(precision_at_k(retrieved_ids, example.relevant_chunk_ids, k))
                recalls.append(recall_at_k(retrieved_ids, example.relevant_chunk_ids, k))
                hit_rates.append(_hit_rate(retrieved_ids, example.relevant_chunk_ids, k))
                if k == max_k:
                    mrr_values.append(mrr(retrieved_ids, example.relevant_chunk_ids))
            summary_by_k[str(k)] = {
                "precision": round(mean(precisions), 4),
                "recall": round(mean(recalls), 4),
                "hit_rate": round(mean(hit_rates), 4),
            }
        modes[name] = {
            "mrr": round(mean(mrr_values), 4),
            "summary_by_k": summary_by_k,
        }

    comparisons: dict[str, Any] = {}
    for hybrid_name in [name for name in retrievers if name != "dense"]:
        improved: dict[str, list[dict[str, Any]]] = {str(k): [] for k in top_ks}
        hurt: dict[str, list[dict[str, Any]]] = {str(k): [] for k in top_ks}
        for example in examples:
            dense_ids = raw_results["dense"][example.id]
            hybrid_ids = raw_results[hybrid_name][example.id]
            for k in top_ks:
                dense_precision = precision_at_k(dense_ids, example.relevant_chunk_ids, k)
                hybrid_precision = precision_at_k(hybrid_ids, example.relevant_chunk_ids, k)
                dense_recall = recall_at_k(dense_ids, example.relevant_chunk_ids, k)
                hybrid_recall = recall_at_k(hybrid_ids, example.relevant_chunk_ids, k)
                if hybrid_recall > dense_recall:
                    improved[str(k)].append(
                        {
                            "id": example.id,
                            "query": example.query,
                            "delta_recall": round(hybrid_recall - dense_recall, 4),
                        }
                    )
                if hybrid_precision < dense_precision:
                    hurt[str(k)].append(
                        {
                            "id": example.id,
                            "query": example.query,
                            "delta_precision": round(hybrid_precision - dense_precision, 4),
                        }
                    )
        comparisons[hybrid_name] = {
            "improved_recall_examples": improved,
            "hurt_precision_examples": hurt,
        }

    report = {
        "measured": True,
        "query_count": len(examples),
        "top_ks": top_ks,
        "modes": modes,
        "comparisons_vs_dense": comparisons,
    }
    report["selected_default_hybrid"] = _choose_default_variant(
        {
            "modes": {name: payload for name, payload in modes.items() if name != "dense"}
            or {"dense": modes["dense"]}
        }
    )
    return report, diagnostics


def summarize_retrieval_diagnostics(diagnostics: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in diagnostics:
        for variant, payload in row["variants"].items():
            if variant == "dense":
                continue
            if payload["first_relevant_moved"] == "up":
                lines.append(f"{row['id']}:{variant}:first relevant moved up")
            elif payload["first_relevant_moved"] == "down":
                lines.append(f"{row['id']}:{variant}:first relevant moved down")
    return lines


def score_generation(
    *,
    answerer: Answerer,
    example: HallucinationExample,
    retrieval_mode: RetrievalMode,
    retrieval_result: Any,
) -> dict[str, Any]:
    generation = answerer.generate(example.question, retrieval_result.hits)
    source_ids = [source.chunk_id for source in generation.sources]
    refusal = bool(generation.refusal.is_refusal)
    valid_citation = has_valid_citation(generation.answer, source_ids) if not refusal else True
    answer_ok = (
        answer_matches(generation.answer, example.acceptable_answers) if not refusal else False
    )
    refusal_correct = example.expected_behavior == "refuse" and refusal
    false_refusal = example.expected_behavior == "answer" and refusal

    hallucinated = False
    unsupported_claim = False
    if example.expected_behavior == "refuse":
        hallucinated = not refusal_correct
        unsupported_claim = hallucinated
    elif not refusal:
        unsupported_claim = (not valid_citation) or (not answer_ok)
        hallucinated = unsupported_claim

    total_cost = None
    if generation.llm_cost_usd is not None:
        total_cost = round(
            float(retrieval_result.embedding_cost_usd) + float(generation.llm_cost_usd), 8
        )

    return {
        "id": example.id,
        "question": example.question,
        "expected_behavior": example.expected_behavior,
        "retrieval_mode": retrieval_mode,
        "answer": generation.answer,
        "refusal": refusal,
        "refusal_reason": generation.refusal.reason,
        "answerability": generation.answerability,
        "source_ids": source_ids,
        "valid_citation": valid_citation,
        "citation_coverage": generation.citation_coverage,
        "answer_matches_gold": answer_ok,
        "refusal_correct": refusal_correct,
        "false_refusal": false_refusal,
        "unsupported_claim": unsupported_claim,
        "hallucinated": hallucinated,
        "cost_usd": total_cost,
        "embedding_tokens": int(retrieval_result.embedding_tokens),
        "llm_tokens_in": generation.llm_tokens_in,
        "llm_tokens_out": generation.llm_tokens_out,
    }


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def mean_optional(values: list[float | None]) -> float | None:
    measured = [float(value) for value in values if value is not None]
    if not measured:
        return None
    return float(sum(measured) / len(measured))


def hallucination_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_refusal_answers = [row for row in rows if not row["refusal"]]
    refusal_examples = [row for row in rows if row["expected_behavior"] == "refuse"]
    answer_examples = [row for row in rows if row["expected_behavior"] == "answer"]
    return {
        "example_count": len(rows),
        "hallucination_rate": round(mean([1.0 if row["hallucinated"] else 0.0 for row in rows]), 4),
        "citation_grounding_failure_rate": round(
            mean([1.0 if not row["valid_citation"] else 0.0 for row in non_refusal_answers]),
            4,
        ),
        "unsupported_claim_rate": round(
            mean([1.0 if row["unsupported_claim"] else 0.0 for row in rows]),
            4,
        ),
        "refusal_correctness_rate": round(
            mean([1.0 if row["refusal_correct"] else 0.0 for row in refusal_examples]),
            4,
        ),
        "false_refusal_rate": round(
            mean([1.0 if row["false_refusal"] else 0.0 for row in answer_examples]),
            4,
        ),
        "supported_answer_rate": round(
            mean(
                [
                    1.0
                    if (not row["refusal"] and row["answer_matches_gold"] and row["valid_citation"])
                    else 0.0
                    for row in answer_examples
                ]
            ),
            4,
        ),
        "citation_coverage": round(
            mean([float(row["citation_coverage"] or 0.0) for row in non_refusal_answers]),
            4,
        ),
        "avg_cost_per_query_usd": _rounded_optional(
            mean_optional([row["cost_usd"] for row in rows]),
            digits=8,
        ),
        "avg_embedding_tokens_per_query": round(
            mean([float(row["embedding_tokens"]) for row in rows]),
            4,
        ),
        "avg_llm_tokens_in_per_query": _rounded_optional(
            mean_optional([row["llm_tokens_in"] for row in rows]),
            digits=4,
        ),
        "avg_llm_tokens_out_per_query": _rounded_optional(
            mean_optional([row["llm_tokens_out"] for row in rows]),
            digits=4,
        ),
    }


def _rounded_optional(value: float | None, *, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def evaluate_hallucination(
    dense_retriever: Retriever,
    hybrid_retriever: Retriever,
    baseline_answerer: Answerer,
    strict_hybrid_answerer: Answerer,
    examples: list[HallucinationExample],
    *,
    top_k: int,
) -> dict[str, Any]:
    dense_rows: list[dict[str, Any]] = []
    hybrid_rows: list[dict[str, Any]] = []

    for example in examples:
        dense_result = dense_retriever.retrieve(
            example.question,
            top_k=top_k,
            rewrite_override=False,
            mode_override="dense",
        )
        hybrid_result = hybrid_retriever.retrieve(
            example.question,
            top_k=top_k,
            rewrite_override=False,
            mode_override="hybrid",
        )
        dense_rows.append(
            score_generation(
                answerer=baseline_answerer,
                example=example,
                retrieval_mode="dense",
                retrieval_result=dense_result,
            )
        )
        hybrid_rows.append(
            score_generation(
                answerer=strict_hybrid_answerer,
                example=example,
                retrieval_mode="hybrid",
                retrieval_result=hybrid_result,
            )
        )

    return {
        "measured": True,
        "rule": {
            "hallucination": (
                "A response is hallucinated when it answers a refusal-required question without refusing, "
                "or when it answers an answer-required question with missing/invalid citations or a gold-mismatched answer."
            ),
            "citation_grounding_failure": "A non-refusal answer without citations that reference returned source IDs.",
            "supported_answer_rate": "Share of answer-required examples answered with valid citations and a gold-matching answer.",
        },
        "baseline_dense": hallucination_summary(dense_rows),
        "strict_grounded_hybrid": hallucination_summary(hybrid_rows),
        "per_example": {
            "baseline_dense": dense_rows,
            "strict_grounded_hybrid": hybrid_rows,
        },
    }


def build_refusal_report(hallucination_report: dict[str, Any]) -> dict[str, Any]:
    dense_rows = hallucination_report["per_example"]["baseline_dense"]
    hybrid_rows = hallucination_report["per_example"]["strict_grounded_hybrid"]
    return {
        "measured": True,
        "baseline_dense": {
            "false_refusal_rate": hallucination_report["baseline_dense"]["false_refusal_rate"],
            "refusal_correctness_rate": hallucination_report["baseline_dense"][
                "refusal_correctness_rate"
            ],
            "supported_answer_rate": hallucination_report["baseline_dense"][
                "supported_answer_rate"
            ],
            "citation_coverage": hallucination_report["baseline_dense"]["citation_coverage"],
            "answerability_breakdown": _answerability_breakdown(dense_rows),
        },
        "strict_grounded_hybrid": {
            "false_refusal_rate": hallucination_report["strict_grounded_hybrid"][
                "false_refusal_rate"
            ],
            "refusal_correctness_rate": hallucination_report["strict_grounded_hybrid"][
                "refusal_correctness_rate"
            ],
            "supported_answer_rate": hallucination_report["strict_grounded_hybrid"][
                "supported_answer_rate"
            ],
            "citation_coverage": hallucination_report["strict_grounded_hybrid"][
                "citation_coverage"
            ],
            "answerability_breakdown": _answerability_breakdown(hybrid_rows),
        },
    }


def _answerability_breakdown(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"answerable": 0, "partially_answerable": 0, "not_answerable": 0}
    for row in rows:
        label = str(row.get("answerability", "not_answerable"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def build_cost_report(hallucination_report: dict[str, Any]) -> dict[str, Any]:
    rows = hallucination_report["per_example"]["strict_grounded_hybrid"]
    measured_costs = [row["cost_usd"] for row in rows if row["cost_usd"] is not None]
    return {
        "measured": True,
        "llm_cost_measured": bool(measured_costs),
        "pricing_source": {
            "embedding": "settings.embeddings.openai.usd_per_1k_tokens for remote embeddings; null for local embeddings",
            "generation": "settings.generation.pricing for remote generation; null when running offline fallback",
        },
        "summary": {
            "avg_embedding_tokens_per_query": round(
                mean([float(row["embedding_tokens"]) for row in rows]), 4
            ),
            "avg_input_tokens_per_query": _rounded_optional(
                mean_optional([row["llm_tokens_in"] for row in rows]),
                digits=4,
            ),
            "avg_output_tokens_per_query": _rounded_optional(
                mean_optional([row["llm_tokens_out"] for row in rows]),
                digits=4,
            ),
            "avg_cost_per_query_usd": _rounded_optional(mean_optional(measured_costs), digits=8),
            "total_cost_usd": _rounded_optional(
                float(sum(measured_costs)) if measured_costs else None, digits=8
            ),
        },
    }


def reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def start_local_api(
    *,
    python_executable: str,
    env: dict[str, str],
    host: str = "127.0.0.1",
    port: int | None = None,
) -> tuple[subprocess.Popen[str], str]:
    chosen_port = port or reserve_port()
    cmd = [
        python_executable,
        "-m",
        "uvicorn",
        "api.app:app",
        "--host",
        host,
        "--port",
        str(chosen_port),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    base_url = f"http://{host}:{chosen_port}"
    deadline = time.time() + 60.0
    with httpx.Client() as client:
        while time.time() < deadline:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(f"API server exited before ready: {stderr.strip()[:400]}")
            try:
                response = client.get(f"{base_url}/readyz", timeout=1.0)
                if response.status_code == 200:
                    return proc, base_url
            except Exception:
                time.sleep(0.5)
    proc.terminate()
    stderr = proc.stderr.read() if proc.stderr else ""
    raise RuntimeError(f"Timed out waiting for local API: {stderr.strip()[:400]}")


async def run_load_test(
    *,
    base_url: str,
    endpoint: str,
    queries: list[str],
    top_k: int,
    concurrency_levels: list[int],
    requests_per_level: int,
    timeout_s: float,
    warmup_requests: int = 5,
) -> dict[str, Any]:
    rows: list[LoadTestRow] = []
    url = base_url.rstrip("/") + endpoint

    async with httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=max(concurrency_levels),
            max_keepalive_connections=max(concurrency_levels),
        ),
        timeout=timeout_s,
    ) as client:
        for i in range(min(warmup_requests, len(queries))):
            payload = {"query": queries[i % len(queries)], "top_k": top_k, "rewrite_query": False}
            with suppress(Exception):
                await client.post(url, json=payload)

        for concurrency in concurrency_levels:
            total_requests = max(requests_per_level, concurrency)
            sem = asyncio.Semaphore(concurrency)
            latencies_s: list[float] = []
            errors: list[str] = []
            started_wall = time.perf_counter()

            async def one_request(
                index: int,
                *,
                limiter: asyncio.Semaphore = sem,
                seen_latencies: list[float] = latencies_s,
                seen_errors: list[str] = errors,
            ) -> None:
                payload = {
                    "query": queries[index % len(queries)],
                    "top_k": top_k,
                    "rewrite_query": False,
                }
                async with limiter:
                    started = time.perf_counter()
                    try:
                        response = await client.post(url, json=payload)
                        if 200 <= response.status_code < 300:
                            seen_latencies.append(time.perf_counter() - started)
                        else:
                            seen_errors.append(f"{response.status_code}:{response.text[:120]}")
                    except Exception as exc:
                        seen_errors.append(str(exc))

            await asyncio.gather(*[one_request(i) for i in range(total_requests)])
            wall_time = time.perf_counter() - started_wall
            stats = summarize_latency(latencies_s)
            rows.append(
                LoadTestRow(
                    concurrency=concurrency,
                    total_requests=total_requests,
                    success_count=len(latencies_s),
                    failure_count=len(errors),
                    failure_rate=round((len(errors) / total_requests), 4),
                    avg_latency_ms=round(stats.avg_ms, 3) if latencies_s else None,
                    p50_latency_ms=round(stats.p50_ms, 3) if latencies_s else None,
                    p95_latency_ms=round(stats.p95_ms, 3) if latencies_s else None,
                    p99_latency_ms=round(stats.p99_ms, 3) if latencies_s else None,
                    sample_errors=errors[:5] or None,
                    wall_time_s=round(wall_time, 3),
                )
            )

    successful_levels = [
        row.concurrency for row in rows if row.success_count > 0 and row.failure_count == 0
    ]
    return {
        "measured": True,
        "base_url": base_url,
        "endpoint": endpoint,
        "results": [asdict(row) for row in rows],
        "max_tested_concurrency_successful": max(successful_levels) if successful_levels else None,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_resume_metrics(
    *,
    dataset_stats: dict[str, Any],
    latency_dense: dict[str, Any],
    latency_hybrid_weighted: dict[str, Any],
    latency_hybrid_rrf: dict[str, Any],
    retrieval: dict[str, Any],
    hallucination: dict[str, Any],
    refusal_report: dict[str, Any],
    cost_report: dict[str, Any],
    load_test: dict[str, Any],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "documents_indexed": dataset_stats.get("documents_indexed")
        if dataset_stats.get("measured")
        else None,
        "chunks_indexed": dataset_stats.get("chunks_indexed")
        if dataset_stats.get("measured")
        else None,
        "vector_index_size_bytes": (
            dataset_stats.get("index_sizes_bytes", {}).get("vector_index")
            if dataset_stats.get("measured")
            else None
        ),
        "avg_latency_ms_dense": latency_dense.get("summary", {}).get("avg_latency_ms")
        if latency_dense.get("measured")
        else None,
        "p95_latency_ms_dense": latency_dense.get("summary", {}).get("p95_latency_ms")
        if latency_dense.get("measured")
        else None,
        "avg_latency_ms_hybrid_weighted": latency_hybrid_weighted.get("summary", {}).get(
            "avg_latency_ms"
        )
        if latency_hybrid_weighted.get("measured")
        else None,
        "p95_latency_ms_hybrid_weighted": latency_hybrid_weighted.get("summary", {}).get(
            "p95_latency_ms"
        )
        if latency_hybrid_weighted.get("measured")
        else None,
        "avg_latency_ms_hybrid_rrf": latency_hybrid_rrf.get("summary", {}).get("avg_latency_ms")
        if latency_hybrid_rrf.get("measured")
        else None,
        "p95_latency_ms_hybrid_rrf": latency_hybrid_rrf.get("summary", {}).get("p95_latency_ms")
        if latency_hybrid_rrf.get("measured")
        else None,
        "max_tested_concurrency_successful": load_test.get("max_tested_concurrency_successful")
        if load_test.get("measured")
        else None,
    }

    if retrieval.get("measured"):
        for name, label in [
            ("dense", "dense"),
            ("hybrid_weighted", "hybrid_weighted"),
            ("hybrid_rrf", "hybrid_rrf"),
        ]:
            mode = retrieval["modes"].get(name)
            if not mode:
                continue
            metrics[f"mrr_{label}"] = mode["mrr"]
            for k in [1, 3, 5, 10]:
                summary = mode["summary_by_k"].get(str(k))
                if not summary:
                    continue
                metrics[f"precision_at_{k}_{label}"] = summary["precision"]
                metrics[f"recall_at_{k}_{label}"] = summary["recall"]
                metrics[f"hit_rate_at_{k}_{label}"] = summary["hit_rate"]

    if hallucination.get("measured"):
        metrics["hallucination_rate_dense"] = hallucination["baseline_dense"]["hallucination_rate"]
        metrics["hallucination_rate_hybrid"] = hallucination["strict_grounded_hybrid"][
            "hallucination_rate"
        ]
        metrics["citation_grounding_failure_rate_dense"] = hallucination["baseline_dense"][
            "citation_grounding_failure_rate"
        ]
        metrics["citation_grounding_failure_rate_hybrid"] = hallucination["strict_grounded_hybrid"][
            "citation_grounding_failure_rate"
        ]

    if refusal_report.get("measured"):
        metrics["false_refusal_rate_dense"] = refusal_report["baseline_dense"]["false_refusal_rate"]
        metrics["false_refusal_rate_hybrid"] = refusal_report["strict_grounded_hybrid"][
            "false_refusal_rate"
        ]
        metrics["supported_answer_rate_hybrid"] = refusal_report["strict_grounded_hybrid"][
            "supported_answer_rate"
        ]
        metrics["citation_coverage_hybrid"] = refusal_report["strict_grounded_hybrid"][
            "citation_coverage"
        ]

    if cost_report.get("measured"):
        metrics["avg_embedding_tokens_per_query"] = cost_report["summary"][
            "avg_embedding_tokens_per_query"
        ]
        metrics["avg_llm_tokens_in_per_query"] = cost_report["summary"][
            "avg_input_tokens_per_query"
        ]
        metrics["avg_llm_tokens_out_per_query"] = cost_report["summary"][
            "avg_output_tokens_per_query"
        ]
        metrics["avg_cost_per_query_usd"] = cost_report["summary"]["avg_cost_per_query_usd"]
        metrics["total_eval_cost_usd"] = cost_report["summary"]["total_cost_usd"]

    return metrics


def build_resume_bullets(metrics: dict[str, Any]) -> str:
    docs = metrics.get("documents_indexed")
    chunks = metrics.get("chunks_indexed")
    p95 = metrics.get("p95_latency_ms_hybrid_rrf")
    halluc_dense = metrics.get("hallucination_rate_dense")
    halluc_hybrid = metrics.get("hallucination_rate_hybrid")
    retrieval_gain = None
    if metrics.get("mrr_hybrid_rrf") is not None and metrics.get("mrr_dense") is not None:
        retrieval_gain = round(float(metrics["mrr_hybrid_rrf"]) - float(metrics["mrr_dense"]), 4)

    parts = []
    if docs is not None and chunks is not None:
        parts.append(f"{docs} indexed documents / {chunks} chunks")
    if p95 is not None:
        parts.append(f"{p95} ms p95 RRF-hybrid retrieval latency")
    if halluc_dense is not None and halluc_hybrid is not None:
        parts.append(f"hallucination rate {halluc_dense} -> {halluc_hybrid}")

    short = "Built a reproducible hybrid RAG evaluation pipeline"
    if parts:
        short += f" ({'; '.join(parts)})."
    else:
        short += "."

    strong = "Implemented dense-vs-hybrid RAG benchmarking with retrieval diagnostics, refusal evaluation, and cost tracking"
    details = []
    if retrieval_gain is not None:
        details.append(f"MRR delta vs dense {retrieval_gain:+.4f}")
    if metrics.get("false_refusal_rate_hybrid") is not None:
        details.append(f"false refusal rate {metrics['false_refusal_rate_hybrid']}")
    if p95 is not None:
        details.append(f"p95 latency {p95} ms")
    if details:
        strong += ": " + ", ".join(details) + "."
    else:
        strong += "."

    senior = (
        "Productionized measurement for a grounded RAG stack with code-generated evidence for corpus scale, "
        "retrieval quality, answer support, and latency"
    )
    if parts:
        senior += f" ({'; '.join(parts)})."
    else:
        senior += "."

    return "\n".join(
        [
            "# Resume Bullets",
            "",
            "## Short Bullet",
            f"- {short}",
            "",
            "## Strong Bullet",
            f"- {strong}",
            "",
            "## Senior/Staff-Style Bullet",
            f"- {senior}",
            "",
            "## Claim Boundaries",
            "- These bullets include only values written into `experiments/metrics/resume_metrics.json` by code execution.",
            "- Null fields in `resume_metrics.json` must not be turned into resume claims.",
        ]
    )


def default_run_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    env.setdefault("RAG_ENV", "dev")
    venv_bin = str((Path(".venv") / "bin").absolute())
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(Path(".venv").absolute())
    env["OPENAI_API_KEY"] = ""
    env["OPENAI_BASE_URL"] = ""
    env["OPENAI_ORG"] = ""
    return env
