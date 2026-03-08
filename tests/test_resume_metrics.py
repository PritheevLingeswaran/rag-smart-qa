from __future__ import annotations

from evaluation.resume_metrics import (
    answer_matches,
    build_cost_report,
    build_refusal_report,
    build_resume_metrics,
    hallucination_summary,
    has_valid_citation,
    normalize_answer,
)


def test_normalize_answer_strips_citations_and_source_suffix() -> None:
    text = "B.Tech - Computer Science Engineering. [resume:p1:c6] (source: resume:p1:c6)"
    assert normalize_answer(text) == "b tech computer science engineering"


def test_answer_matches_uses_normalized_exact_match() -> None:
    assert answer_matches(
        "2024-2028 (Expected) [Pritheev_Resume.pdf:p1:c6]",
        ["2024 2028 expected"],
    )


def test_has_valid_citation_requires_returned_source_ids() -> None:
    assert has_valid_citation("Yes [a] [b]", ["a", "b", "c"]) is True
    assert has_valid_citation("Yes [a] [missing]", ["a", "b", "c"]) is False
    assert has_valid_citation("Yes", ["a"]) is False


def test_hallucination_summary_aggregates_rates() -> None:
    rows = [
        {
            "hallucinated": True,
            "valid_citation": False,
            "unsupported_claim": True,
            "refusal_correct": False,
            "false_refusal": False,
            "refusal": False,
            "expected_behavior": "answer",
            "cost_usd": None,
            "embedding_tokens": 0,
            "llm_tokens_in": None,
            "llm_tokens_out": None,
            "answer_matches_gold": False,
            "citation_coverage": 0.0,
        },
        {
            "hallucinated": False,
            "valid_citation": True,
            "unsupported_claim": False,
            "refusal_correct": True,
            "false_refusal": False,
            "refusal": True,
            "expected_behavior": "refuse",
            "cost_usd": None,
            "embedding_tokens": 0,
            "llm_tokens_in": None,
            "llm_tokens_out": None,
            "answer_matches_gold": False,
            "citation_coverage": None,
        },
    ]
    summary = hallucination_summary(rows)
    assert summary["hallucination_rate"] == 0.5
    assert summary["refusal_correctness_rate"] == 1.0
    assert summary["citation_grounding_failure_rate"] == 1.0
    assert summary["avg_cost_per_query_usd"] is None


def test_build_resume_metrics_only_includes_measured_values() -> None:
    metrics = build_resume_metrics(
        dataset_stats={
            "measured": True,
            "documents_indexed": 2,
            "chunks_indexed": 9,
            "index_sizes_bytes": {"vector_index": 10},
        },
        latency_dense={"measured": False},
        latency_hybrid_weighted={
            "measured": True,
            "summary": {
                "avg_latency_ms": 1.0,
                "p95_latency_ms": 2.0,
                "p99_latency_ms": 3.0,
            },
        },
        latency_hybrid_rrf={
            "measured": True,
            "summary": {
                "avg_latency_ms": 0.8,
                "p95_latency_ms": 1.5,
                "p99_latency_ms": 2.0,
            },
        },
        retrieval={
            "measured": True,
            "modes": {
                "dense": {
                    "mrr": 0.1,
                    "summary_by_k": {"5": {"precision": 0.1, "recall": 0.3, "hit_rate": 0.5}},
                },
                "hybrid_weighted": {
                    "mrr": 0.15,
                    "summary_by_k": {"5": {"precision": 0.2, "recall": 0.4, "hit_rate": 0.6}},
                },
                "hybrid_rrf": {
                    "mrr": 0.2,
                    "summary_by_k": {"5": {"precision": 0.25, "recall": 0.45, "hit_rate": 0.7}},
                },
            },
        },
        hallucination={
            "measured": True,
            "baseline_dense": {
                "hallucination_rate": 0.5,
                "citation_grounding_failure_rate": 0.2,
            },
            "strict_grounded_hybrid": {
                "hallucination_rate": 0.1,
                "citation_grounding_failure_rate": 0.0,
            },
        },
        refusal_report={
            "measured": True,
            "baseline_dense": {"false_refusal_rate": 0.3},
            "strict_grounded_hybrid": {
                "false_refusal_rate": 0.2,
                "supported_answer_rate": 0.8,
                "citation_coverage": 0.6,
            },
        },
        cost_report={
            "measured": True,
            "summary": {
                "avg_embedding_tokens_per_query": 12.0,
                "avg_input_tokens_per_query": None,
                "avg_output_tokens_per_query": None,
                "avg_cost_per_query_usd": None,
                "total_cost_usd": None,
            },
        },
        load_test={"measured": False},
    )
    assert metrics["documents_indexed"] == 2
    assert metrics["precision_at_5_hybrid_weighted"] == 0.2
    assert metrics["precision_at_5_hybrid_rrf"] == 0.25
    assert metrics["max_tested_concurrency_successful"] is None


def test_build_refusal_and_cost_reports_keep_null_costs_when_offline() -> None:
    hallucination_report = {
        "measured": True,
        "baseline_dense": {
            "false_refusal_rate": 0.4,
            "refusal_correctness_rate": 1.0,
            "supported_answer_rate": 0.5,
            "citation_coverage": 0.2,
        },
        "strict_grounded_hybrid": {
            "false_refusal_rate": 0.2,
            "refusal_correctness_rate": 1.0,
            "supported_answer_rate": 0.7,
            "citation_coverage": 0.8,
        },
        "per_example": {
            "baseline_dense": [{"answerability": "not_answerable"}],
            "strict_grounded_hybrid": [
                {
                    "answerability": "answerable",
                    "cost_usd": None,
                    "embedding_tokens": 10,
                    "llm_tokens_in": None,
                    "llm_tokens_out": None,
                }
            ],
        },
    }
    refusal = build_refusal_report(hallucination_report)
    cost = build_cost_report(hallucination_report)
    assert refusal["strict_grounded_hybrid"]["answerability_breakdown"]["answerable"] == 1
    assert cost["summary"]["avg_embedding_tokens_per_query"] == 10.0
    assert cost["summary"]["avg_cost_per_query_usd"] is None
