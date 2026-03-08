from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

from retrieval.bm25 import BM25TextNormalizer
from utils.settings import RerankConfig

"""Optional reranking.

Heavy dependencies are loaded only when the configured provider needs them.
"""


@dataclass(frozen=True)
class RerankHit:
    idx: int
    score: float


class BaseReranker:
    def rerank(
        self,
        query: str,
        passages: list[str],
        *,
        base_scores: list[float],
        top_k: int,
    ) -> list[RerankHit]:
        raise NotImplementedError


class LexicalReranker(BaseReranker):
    def __init__(self, cfg: RerankConfig) -> None:
        self.cfg = cfg
        self._normalizer = BM25TextNormalizer()

    def rerank(
        self,
        query: str,
        passages: list[str],
        *,
        base_scores: list[float],
        top_k: int,
    ) -> list[RerankHit]:
        query_tokens = self._normalizer.tokenize(query)
        query_set = set(query_tokens)
        ranked: list[tuple[int, float]] = []

        for idx, (passage, base_score) in enumerate(zip(passages, base_scores, strict=False)):
            doc_tokens = self._normalizer.tokenize(passage)
            doc_set = set(doc_tokens)
            overlap = len(query_set & doc_set)
            coverage = (overlap / len(query_set)) if query_set else 0.0
            lexical_score = coverage + (0.15 if query.lower() in passage.lower() else 0.0)
            if coverage < float(self.cfg.min_query_term_coverage):
                lexical_score *= 0.5
            score = float(self.cfg.query_weight) * lexical_score + float(
                self.cfg.retrieval_weight
            ) * float(base_score)
            ranked.append((idx, float(score)))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return [RerankHit(idx=i, score=s) for i, s in ranked[:top_k]]


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "sentence-transformers is not installed. Install it or disable retrieval.rerank.enabled."
            ) from e
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        passages: list[str],
        *,
        base_scores: list[float],
        top_k: int,
    ) -> list[RerankHit]:
        del base_scores
        pairs = [(query, passage) for passage in passages]
        scores = cast(list[Any], self.model.predict(pairs))
        ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)[:top_k]
        return [RerankHit(idx=i, score=float(s)) for i, s in ranked]


@lru_cache(maxsize=4)
def build_reranker(cfg_key: tuple[object, ...]) -> BaseReranker:
    provider = str(cfg_key[0])
    if provider == "cross_encoder":
        return CrossEncoderReranker(model_name=str(cfg_key[1]))
    query_weight = cast(float, cfg_key[2])
    retrieval_weight = cast(float, cfg_key[3])
    min_query_term_coverage = cast(float, cfg_key[4])
    cfg = RerankConfig(
        provider=provider,  # type: ignore[arg-type]
        model_name=str(cfg_key[1]),
        query_weight=query_weight,
        retrieval_weight=retrieval_weight,
        min_query_term_coverage=min_query_term_coverage,
    )
    return LexicalReranker(cfg)


def build_reranker_from_config(cfg: RerankConfig) -> BaseReranker:
    return build_reranker(
        (
            cfg.provider,
            cfg.model_name,
            cfg.query_weight,
            cfg.retrieval_weight,
            cfg.min_query_term_coverage,
        )
    )
