from __future__ import annotations

from dataclasses import dataclass

"""Optional reranking.

This module is intentionally written to avoid importing heavy optional dependencies
(`sentence_transformers`) unless reranking is enabled.
"""


@dataclass(frozen=True)
class RerankHit:
    idx: int
    score: float


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "sentence-transformers is not installed. Install it or disable retrieval.rerank.enabled."
            ) from e
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, passages: list[str], top_k: int) -> list[RerankHit]:
        pairs = [(query, p) for p in passages]
        scores = self.model.predict(pairs)
        ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)[:top_k]
        return [RerankHit(idx=i, score=float(s)) for i, s in ranked]
