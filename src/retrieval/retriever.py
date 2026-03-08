from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from embeddings.factory import build_embeddings_backend
from retrieval.bm25 import BM25DocHit, BM25PersistentIndex
from retrieval.corpus import load_chunks_jsonl
from retrieval.query_rewrite import rewrite_query
from retrieval.rerank import build_reranker_from_config
from retrieval.vector_store import IndexedChunk, SearchHit, VectorStore
from utils.logging import get_logger
from utils.openai_client import OpenAIClient
from utils.settings import Settings

log = get_logger(__name__)

RetrievalMode = Literal["dense", "hybrid", "bm25"]


@dataclass
class RetrievalOutput:
    query_used: str
    hits: list[SearchHit]
    embedding_tokens: int
    embedding_cost_usd: float
    debug: dict[str, Any] | None = None


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
        self._query_cache: OrderedDict[tuple[object, ...], RetrievalOutput] = OrderedDict()

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
    ) -> tuple[list[SearchHit], dict[str, Any]]:
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
        explanation: dict[str, Any] = {
            "fusion_method": cfg.fusion_method,
            "candidate_count": len(candidate_ids),
            "rrf_k": int(cfg.rrf_k),
            "dense_weight": alpha,
        }
        dense_rank = {h.chunk.chunk_id: idx for idx, h in enumerate(dense_hits, start=1)}
        sparse_rank = {h.chunk_id: idx for idx, h in enumerate(sparse_hits, start=1)}
        for cid in candidate_ids:
            d = dense_map.get(cid, 0.0)
            s = sparse_norm.get(cid, 0.0)
            if cfg.fusion_method == "rrf":
                fused_score = 0.0
                if cid in dense_rank:
                    fused_score += 1.0 / (float(cfg.rrf_k) + float(dense_rank[cid]))
                if cid in sparse_rank:
                    fused_score += 1.0 / (float(cfg.rrf_k) + float(sparse_rank[cid]))
            else:
                fused_score = alpha * d + (1.0 - alpha) * s

            # Prefer the chunk object already returned by dense retrieval; otherwise load from corpus.
            chunk = dense_chunks.get(cid) or chunk_by_id.get(cid)
            if chunk is None:
                # Corpus drift (chunks.jsonl changed) or inconsistent build. Skip safely.
                continue
            fused.append(SearchHit(chunk=chunk, score=float(fused_score)))

        fused.sort(key=lambda x: float(x.score), reverse=True)
        return fused[:top_k], explanation

    def _get_cached(self, key: tuple[object, ...]) -> RetrievalOutput | None:
        if not self.settings.retrieval.cache.enabled:
            return None
        cached = self._query_cache.get(key)
        if cached is None:
            return None
        self._query_cache.move_to_end(key)
        return cached

    def _set_cached(self, key: tuple[object, ...], value: RetrievalOutput) -> None:
        if not self.settings.retrieval.cache.enabled:
            return
        self._query_cache[key] = value
        self._query_cache.move_to_end(key)
        max_entries = int(self.settings.retrieval.cache.max_entries)
        while len(self._query_cache) > max_entries:
            self._query_cache.popitem(last=False)

    def _bm25_only_hits(
        self,
        query: str,
        *,
        top_k: int,
        filter_source_substr: str | None,
    ) -> list[SearchHit]:
        bm25, chunk_by_id = self._lazy_load_bm25_and_corpus()

        def _filter_fn(cid: str) -> bool:
            if not filter_source_substr:
                return True
            c = chunk_by_id.get(cid)
            return c is not None and filter_source_substr in c.source

        sparse_hits = bm25.query(
            query,
            top_k=max(int(top_k), int(self.settings.retrieval.hybrid.bm25_k)),
            filter_fn=_filter_fn,
        )
        sparse_norm = _normalize_bm25(sparse_hits)
        hits: list[SearchHit] = []
        for h in sparse_hits:
            chunk = chunk_by_id.get(h.chunk_id)
            if chunk is None:
                continue
            hits.append(SearchHit(chunk=chunk, score=float(sparse_norm.get(h.chunk_id, 0.0))))
            if len(hits) >= top_k:
                break
        return hits

    @staticmethod
    def _apply_min_score_cutoff(
        hits: list[SearchHit], min_score: float
    ) -> tuple[list[SearchHit], bool]:
        if not hits:
            return hits, False
        filtered = [h for h in hits if float(h.score) >= float(min_score)]
        # Two-stage gating: keep candidates for answer-stage refusal if cutoff wipes all.
        if filtered:
            return filtered, True
        return hits, False

    def retrieve(
        self,
        question: str,
        top_k: int,
        filter_source_substr: str | None = None,
        rewrite_override: bool | None = None,
        mode_override: RetrievalMode | None = None,
    ) -> RetrievalOutput:
        return self.retrieve_with_debug(
            question=question,
            top_k=top_k,
            filter_source_substr=filter_source_substr,
            rewrite_override=rewrite_override,
            mode_override=mode_override,
        )

    def retrieve_with_debug(
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
        cache_key = (
            mode,
            query,
            int(top_k),
            filter_source_substr or "",
            bool(do_rewrite),
            self.settings.retrieval.hybrid.fusion_method,
            self.settings.retrieval.rerank.enabled,
            self.settings.retrieval.rerank.provider,
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        debug: dict[str, Any] = {
            "mode": mode,
            "question": question,
            "query_used": query,
            "rewrite_applied": bool(do_rewrite),
            "top_k_requested": int(top_k),
            "threshold_min_score": float(self.settings.retrieval.min_score),
            "stage_counts": {},
            "top_scores": {},
            "top_ids": {},
        }
        log.info(
            "retrieval.query_rewrite",
            mode=mode,
            rewrite_applied=bool(do_rewrite),
            query_used=query,
        )

        if mode == "bm25":
            hits = self._bm25_only_hits(
                query, top_k=int(top_k), filter_source_substr=filter_source_substr
            )
            hits, threshold_applied = self._apply_min_score_cutoff(
                hits, float(self.settings.retrieval.min_score)
            )
            top_scores = [
                round(float(h.score), 6) for h in hits[: self.settings.retrieval.debug_top_n]
            ]
            debug["stage_counts"] = {
                "bm25_hits": len(hits),
                "final_hits": len(hits),
            }
            debug["top_scores"] = {"bm25": top_scores, "final": top_scores}
            debug["top_ids"] = {
                "bm25": [h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]],
                "final": [h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]],
            }
            debug["threshold_applied"] = threshold_applied
            log.info(
                "retrieval.final",
                mode=mode,
                bm25_hits=len(hits),
                threshold_applied=bool(threshold_applied),
                num_hits=len(hits),
                top_scores=top_scores,
            )
            output = RetrievalOutput(
                query_used=query,
                hits=hits,
                embedding_tokens=0,
                embedding_cost_usd=0.0,
                debug=debug,
            )
            self._set_cached(cache_key, output)
            return output

        # Dense retrieval always happens (we need embeddings anyway to answer). We can still reduce
        # dense candidates in hybrid if you want, but in practice a slightly larger dense_k improves stability.
        emb = self.embedder.embed_query(query)
        q_vec = emb.vectors[0]

        dense_k = int(self.settings.retrieval.hybrid.dense_k) if mode == "hybrid" else int(top_k)
        dense_k = max(int(top_k), dense_k)
        dense_hits = self.store.search(
            q_vec, top_k=dense_k, filter_source_substr=filter_source_substr
        )
        dense_top_scores = [
            round(float(h.score), 6) for h in dense_hits[: self.settings.retrieval.debug_top_n]
        ]
        log.info(
            "retrieval.dense_hits",
            mode=mode,
            dense_k=dense_k,
            num_hits=len(dense_hits),
            top_scores=dense_top_scores,
        )
        debug["stage_counts"] = {"dense_hits": len(dense_hits)}
        debug["top_scores"] = {"dense": dense_top_scores}
        debug["top_ids"] = {
            "dense": [h.chunk.chunk_id for h in dense_hits[: self.settings.retrieval.debug_top_n]]
        }

        hits = dense_hits[:top_k]

        if mode == "hybrid":
            bm25, chunk_by_id = self._lazy_load_bm25_and_corpus()

            def _filter_fn(cid: str) -> bool:
                if not filter_source_substr:
                    return True
                c = chunk_by_id.get(cid)
                return c is not None and filter_source_substr in c.source

            sparse_k = int(self.settings.retrieval.hybrid.bm25_k)
            sparse_hits = bm25.query(query, top_k=max(int(top_k), sparse_k), filter_fn=_filter_fn)
            sparse_hits = [
                hit
                for hit in sparse_hits
                if float(hit.score) >= float(self.settings.retrieval.hybrid.min_sparse_score)
            ]
            sparse_norm = _normalize_bm25(sparse_hits)
            sparse_top_scores = [
                round(float(sparse_norm.get(h.chunk_id, 0.0)), 6)
                for h in sparse_hits[: self.settings.retrieval.debug_top_n]
            ]
            log.info(
                "retrieval.bm25_hits",
                mode=mode,
                bm25_k=sparse_k,
                num_hits=len(sparse_hits),
                top_scores=sparse_top_scores,
            )

            hits, fusion_debug = self._fuse_dense_and_sparse(
                dense_hits=dense_hits,
                sparse_hits=sparse_hits,
                chunk_by_id=chunk_by_id,
                top_k=top_k,
            )
            fusion_top_scores = [
                round(float(h.score), 6) for h in hits[: self.settings.retrieval.debug_top_n]
            ]
            log.info(
                "retrieval.fusion_hits",
                mode=mode,
                num_hits=len(hits),
                top_scores=fusion_top_scores,
            )
            debug["stage_counts"]["bm25_hits"] = len(sparse_hits)
            debug["stage_counts"]["fusion_hits"] = len(hits)
            debug["top_scores"]["bm25"] = sparse_top_scores
            debug["top_scores"]["fusion"] = fusion_top_scores
            debug["top_ids"]["bm25"] = [
                h.chunk_id for h in sparse_hits[: self.settings.retrieval.debug_top_n]
            ]
            debug["top_ids"]["fusion"] = [
                h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]
            ]
            debug["fusion"] = fusion_debug

        # Optional reranker runs *after* fusion (so it can improve precision of the hybrid union).
        if self.settings.retrieval.rerank.enabled and hits:
            rr = build_reranker_from_config(self.settings.retrieval.rerank)
            reranked = rr.rerank(
                query,
                [h.chunk.text for h in hits],
                base_scores=[float(h.score) for h in hits],
                top_k=top_k,
            )
            hits = [
                SearchHit(chunk=hits[r.idx].chunk, score=min(1.0, max(0.0, float(r.score))))
                for r in reranked
            ]
            rerank_top_scores = [
                round(float(h.score), 6) for h in hits[: self.settings.retrieval.debug_top_n]
            ]
            log.info(
                "retrieval.rerank_hits",
                mode=mode,
                num_hits=len(hits),
                top_scores=rerank_top_scores,
            )
            debug["stage_counts"]["rerank_hits"] = len(hits)
            debug["top_scores"]["rerank"] = rerank_top_scores
            debug["top_ids"]["rerank"] = [
                h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]
            ]

        # Min-score cutoff.
        hits, threshold_applied = self._apply_min_score_cutoff(
            hits, float(self.settings.retrieval.min_score)
        )
        final_top_scores = [
            round(float(h.score), 6) for h in hits[: self.settings.retrieval.debug_top_n]
        ]
        log.info(
            "retrieval.final",
            mode=mode,
            applied_threshold=float(self.settings.retrieval.min_score),
            threshold_applied=bool(threshold_applied),
            num_hits=len(hits),
            top_scores=final_top_scores,
            embedding_tokens=int(emb.total_tokens),
        )
        debug["stage_counts"]["final_hits"] = len(hits)
        debug["top_scores"]["final"] = final_top_scores
        debug["top_ids"]["final"] = [
            h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]
        ]
        debug["threshold_applied"] = threshold_applied
        debug["embedding_tokens"] = int(emb.total_tokens)

        output = RetrievalOutput(
            query_used=query,
            hits=hits,
            embedding_tokens=emb.total_tokens,
            embedding_cost_usd=emb.cost_usd,
            debug=debug,
        )
        self._set_cached(cache_key, output)
        return output
