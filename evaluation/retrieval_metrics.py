from __future__ import annotations

from dataclasses import dataclass


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for x in top if x in relevant) / len(top)


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    return sum(1 for x in top if x in relevant) / len(relevant)


def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, x in enumerate(retrieved, start=1):
        if x in relevant:
            return 1.0 / i
    return 0.0


@dataclass(frozen=True)
class RetrievalMetrics:
    precision: float
    recall: float
    mrr: float


@dataclass(frozen=True)
class HybridVsDense:
    dense: RetrievalMetrics
    hybrid: RetrievalMetrics

    @property
    def delta_precision(self) -> float:
        return float(self.hybrid.precision - self.dense.precision)

    @property
    def delta_recall(self) -> float:
        return float(self.hybrid.recall - self.dense.recall)

    @property
    def delta_mrr(self) -> float:
        return float(self.hybrid.mrr - self.dense.mrr)


def compute_metrics(retrieved_ids: list[str], relevant: set[str], k: int) -> RetrievalMetrics:
    return RetrievalMetrics(
        precision=precision_at_k(retrieved_ids, relevant, k),
        recall=recall_at_k(retrieved_ids, relevant, k),
        mrr=mrr(retrieved_ids, relevant),
    )


def compare_hybrid_vs_dense(
    *,
    dense_retrieved: list[str],
    hybrid_retrieved: list[str],
    relevant: set[str],
    k: int,
) -> HybridVsDense:
    """Compute retrieval metrics for dense-only and hybrid for the same example.

    This function is used by evaluation to report where hybrid retrieval:
    - improves recall (retrieves more relevant chunks in top-k)
    - hurts precision (pulls in more non-relevant chunks in top-k)
    """

    return HybridVsDense(
        dense=compute_metrics(dense_retrieved, relevant, k),
        hybrid=compute_metrics(hybrid_retrieved, relevant, k),
    )


def improved_recall_case(cmp: HybridVsDense, *, min_gain: float = 1e-9) -> bool:
    return cmp.delta_recall > min_gain


def hurt_precision_case(cmp: HybridVsDense, *, min_drop: float = 1e-9) -> bool:
    return cmp.delta_precision < -min_drop
