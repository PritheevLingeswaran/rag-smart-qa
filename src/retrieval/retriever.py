from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from embeddings.factory import build_embeddings_backend
from retrieval.bm25 import BM25DocHit, BM25PersistentIndex
from retrieval.corpus import load_chunks_jsonl
from retrieval.query_rewrite import rewrite_query
from retrieval.rerank import CrossEncoderReranker
from retrieval.vector_store import IndexedChunk, SearchHit, VectorStore
from utils.openai_client import OpenAIClient
from utils.settings import Settings

RetrievalMode = Literal["dense", "hybrid"]


@dataclass
class RetrievalOutput:
    query_used: str
    hits: list[SearchHit]
    embedding_tokens: int
    embedding_cost_usd: float


def _normalize_bm25(hits: list[BM25DocHit]) -> dict[str, float]:
    """Normalize BM25 scores into [0, 1] using max-score scaling.

    Why: BM25 scores are unbounded and not directly comparable to dense similarity scores.
    We use max-score scaling because it is stable, monotonic, and cheap.

    Tradeoff: scores are only *relative* within the returned sparse top-k.
    """

    if not hits:
        return {}
    max_s = max(h.score for h in hits)
    if max_s <= 0:
        return {h.chunk_id: 0.0 for h in hits}
    return {h.chunk_id: float(h.score / max_s) for h in hits}


class Retriever:
    """Retriever supporting dense-only and true hybrid retrieval.

    Hybrid requirements implemented:
    - BM25 scored over the *full corpus* (via a persistent BM25 index).
    - Dense + sparse fusion via tunable weight (config-driven).
    - Candidate sets are independently retrieved then fused (union), not "BM25 over dense hits".
    """

    def __init__(self, settings: Settings, store: VectorStore) -> None:
        self.settings = settings
        self.store = store
        self.embedder = build_embeddings_backend(settings)

        # Reuse OpenAI settings for rewrite model (OpenAI-compatible).
        oai = settings.embeddings.openai
        self.rewrite_client = OpenAIClient(
            api_key=oai.api_key,
            base_url=oai.base_url,
            organization=oai.organization,
            timeout_s=oai.request_timeout_s,
            max_retries=oai.max_retries,
        )

        # Lazy-loaded sparse resources (only when hybrid retrieval is used).
        self._bm25: BM25PersistentIndex | None = None
        self._chunk_by_id: dict[str, IndexedChunk] | None = None

    def _lazy_load_bm25_and_corpus(self) -> tuple[BM25PersistentIndex, dict[str, IndexedChunk]]:
        if self._bm25 is None:
            bm25_dir = str(Path(self.settings.paths.indexes_dir) / "bm25")
            self._bm25 = BM25PersistentIndex.load(bm25_dir)

        if self._chunk_by_id is None:
            chunks_path = str(Path(self.settings.paths.chunks_dir) / "chunks.jsonl")
            _, by_id = load_chunks_jsonl(chunks_path)
            self._chunk_by_id = by_id

        return self._bm25, self._chunk_by_id

    def _fuse_dense_and_sparse(
        self,
        *,
        dense_hits: list[SearchHit],
        sparse_hits: list[BM25DocHit],
        chunk_by_id: dict[str, IndexedChunk],
        top_k: int,
    ) -> list[SearchHit]:
        cfg = self.settings.retrieval.hybrid

        # Dense scores are already in [0,1]. Sparse scores are normalized to [0,1].
        sparse_norm = _normalize_bm25(sparse_hits)
        dense_map: dict[str, float] = {h.chunk.chunk_id: float(h.score) for h in dense_hits}
        dense_chunks: dict[str, IndexedChunk] = {h.chunk.chunk_id: h.chunk for h in dense_hits}

        alpha = float(cfg.dense_weight)
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("retrieval.hybrid.dense_weight must be in [0,1]")

        # Union of candidates: this is where hybrid recall gains come from.
        candidate_ids = set(dense_map.keys()) | set(sparse_norm.keys())

        fused: list[SearchHit] = []
        for cid in candidate_ids:
            d = dense_map.get(cid, 0.0)
            s = sparse_norm.get(cid, 0.0)
            fused_score = alpha * d + (1.0 - alpha) * s

            # Prefer the chunk object already returned by dense retrieval; otherwise load from corpus.
            chunk = dense_chunks.get(cid) or chunk_by_id.get(cid)
            if chunk is None:
                # Corpus drift (chunks.jsonl changed) or inconsistent build. Skip safely.
                continue
            fused.append(SearchHit(chunk=chunk, score=float(fused_score)))

        fused.sort(key=lambda x: float(x.score), reverse=True)
        return fused[:top_k]

    def retrieve(
        self,
        question: str,
        top_k: int,
        filter_source_substr: str | None = None,
        rewrite_override: bool | None = None,
        mode_override: RetrievalMode | None = None,
    ) -> RetrievalOutput:
        # Decide mode.
        mode: RetrievalMode
        if mode_override is not None:
            mode = mode_override
        else:
            mode = "hybrid" if self.settings.retrieval.hybrid.enabled else "dense"

        do_rewrite = (
            self.settings.retrieval.query_rewrite.enabled
            if rewrite_override is None
            else rewrite_override
        )
        query = (
            rewrite_query(self.settings, self.rewrite_client, question) if do_rewrite else question
        )

        # Dense retrieval always happens (we need embeddings anyway to answer). We can still reduce
        # dense candidates in hybrid if you want, but in practice a slightly larger dense_k improves stability.
        emb = self.embedder.embed_query(query)
        q_vec = emb.vectors[0]

        dense_k = int(self.settings.retrieval.hybrid.dense_k) if mode == "hybrid" else int(top_k)
        dense_k = max(int(top_k), dense_k)
        dense_hits = self.store.search(
            q_vec, top_k=dense_k, filter_source_substr=filter_source_substr
        )

        hits = dense_hits[:top_k]

        if mode == "hybrid":
            bm25, chunk_by_id = self._lazy_load_bm25_and_corpus()

            def _filter_fn(cid: str) -> bool:
                if not filter_source_substr:
                    return True
                c = chunk_by_id.get(cid)
                return bool(c) and (filter_source_substr in c.source)

            sparse_k = int(self.settings.retrieval.hybrid.bm25_k)
            sparse_hits = bm25.query(query, top_k=max(int(top_k), sparse_k), filter_fn=_filter_fn)

            hits = self._fuse_dense_and_sparse(
                dense_hits=dense_hits,
                sparse_hits=sparse_hits,
                chunk_by_id=chunk_by_id,
                top_k=top_k,
            )

        # Optional reranker runs *after* fusion (so it can improve precision of the hybrid union).
        if self.settings.retrieval.rerank.enabled and hits:
            rr = CrossEncoderReranker(self.settings.retrieval.rerank.model_name)
            reranked = rr.rerank(query, [h.chunk.text for h in hits], top_k=top_k)
            hits = [
                SearchHit(chunk=hits[r.idx].chunk, score=min(1.0, max(0.0, float(r.score))))
                for r in reranked
            ]

        # Min-score cutoff.
        hits = [h for h in hits if float(h.score) >= float(self.settings.retrieval.min_score)]

        return RetrievalOutput(
            query_used=query,
            hits=hits,
            embedding_tokens=emb.total_tokens,
            embedding_cost_usd=emb.cost_usd,
        )
