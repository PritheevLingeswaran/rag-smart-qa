from __future__ import annotations

import time
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from embeddings.factory import build_embeddings_backend
from retrieval.bm25 import BM25DocHit, BM25PersistentIndex, BM25TextNormalizer
from retrieval.corpus import load_chunks_jsonl
from retrieval.query_planning import QueryPlan, build_query_plan
from retrieval.rerank import build_reranker_from_config
from retrieval.vector_store import IndexedChunk, SearchHit, VectorStore
from utils.hash import sha256_file
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


class Retriever:
    """Retriever supporting dense-only and true hybrid retrieval.

    Hybrid requirements implemented:
    - BM25 scored over the *full corpus* (via a persistent BM25 index).
    - Dense + sparse fusion via Reciprocal Rank Fusion only.
    - Candidate sets are independently retrieved then fused (union), not "BM25 over dense hits".
    - Reranking is always applied after fusion when candidates exist.
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

        dense_chunks: dict[str, IndexedChunk] = {h.chunk.chunk_id: h.chunk for h in dense_hits}
        dense_score = {h.chunk.chunk_id: float(h.score) for h in dense_hits}
        bm25_score = {h.chunk_id: float(h.score) for h in sparse_hits}

        # Union of candidates: this is where hybrid recall gains come from.
        candidate_ids = {h.chunk.chunk_id for h in dense_hits} | {h.chunk_id for h in sparse_hits}

        fused: list[SearchHit] = []
        fusion_explanation: dict[str, Any] = {
            "fusion_method": "rrf",
            "candidate_count": len(candidate_ids),
            "rrf_k": int(cfg.rrf_k),
        }
        dense_rank = {h.chunk.chunk_id: idx for idx, h in enumerate(dense_hits, start=1)}
        sparse_rank = {h.chunk_id: idx for idx, h in enumerate(sparse_hits, start=1)}
        for cid in candidate_ids:
            fused_score = 0.0
            if cid in dense_rank:
                fused_score += 1.0 / (float(cfg.rrf_k) + float(dense_rank[cid]))
            if cid in sparse_rank:
                fused_score += 1.0 / (float(cfg.rrf_k) + float(sparse_rank[cid]))

            # Prefer the chunk object already returned by dense retrieval; otherwise load from corpus.
            chunk = dense_chunks.get(cid) or chunk_by_id.get(cid)
            if chunk is None:
                # Corpus drift (chunks.jsonl changed) or inconsistent build. Skip safely.
                continue
            explanation = {
                "dense_score": dense_score.get(cid),
                "bm25_score": bm25_score.get(cid),
                "dense_rank": dense_rank.get(cid),
                "bm25_rank": sparse_rank.get(cid),
                "dense_rrf": (
                    1.0 / (float(cfg.rrf_k) + float(dense_rank[cid]))
                    if cid in dense_rank
                    else 0.0
                ),
                "bm25_rrf": (
                    1.0 / (float(cfg.rrf_k) + float(sparse_rank[cid]))
                    if cid in sparse_rank
                    else 0.0
                ),
                "fusion_score": float(fused_score),
                "final_rank_reason": "ranked by reciprocal rank fusion over dense and BM25 ranks",
            }
            fused.append(SearchHit(chunk=chunk, score=float(fused_score), explanation=explanation))

        fused.sort(key=lambda x: float(x.score), reverse=True)
        ranked = [
            SearchHit(
                chunk=h.chunk,
                score=h.score,
                explanation={**h.explanation, "fusion_rank": idx},
            )
            for idx, h in enumerate(fused[:top_k], start=1)
        ]
        return ranked, fusion_explanation

    def _cache_identity(self) -> tuple[object, ...]:
        chunks_path = Path(self.settings.paths.chunks_dir) / "chunks.jsonl"
        bm25_meta = Path(self.settings.paths.indexes_dir) / "bm25" / "meta.json"
        corpus_hash = sha256_file(chunks_path) if chunks_path.exists() else "missing"
        bm25_mtime = bm25_meta.stat().st_mtime_ns if bm25_meta.exists() else 0
        return (
            self.settings.embeddings.provider,
            self.settings.embeddings.model,
            self.settings.embeddings.sentence_transformers.model_name,
            BM25PersistentIndex.INDEX_VERSION,
            self.settings.vector_store.provider,
            self.settings.vector_store.chroma.collection_name,
            corpus_hash,
            bm25_mtime,
        )

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
        lexical_query: str,
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
            lexical_query,
            top_k=max(int(top_k), int(self.settings.retrieval.hybrid.bm25_k)),
            filter_fn=_filter_fn,
        )
        hits: list[SearchHit] = []
        for rank, h in enumerate(sparse_hits, start=1):
            chunk = chunk_by_id.get(h.chunk_id)
            if chunk is None:
                continue
            hits.append(
                SearchHit(
                    chunk=chunk,
                    score=float(h.score),
                    explanation={
                        "dense_score": None,
                        "bm25_score": float(h.score),
                        "bm25_rank": rank,
                        "final_rank_reason": "BM25 lexical fallback result",
                    },
                )
            )
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

    def _expand_related_chunks(
        self,
        hits: list[SearchHit],
        chunk_by_id: dict[str, IndexedChunk],
        *,
        max_extra: int,
    ) -> list[SearchHit]:
        if max_extra <= 0:
            return hits
        out = list(hits)
        seen = {h.chunk.chunk_id for h in out}
        extras = 0
        for hit in hits:
            match = re.search(r":p(\d+):c(\d+)$", hit.chunk.chunk_id)
            if not match:
                continue
            page = int(match.group(1))
            idx = int(match.group(2))
            prefix = hit.chunk.chunk_id[: match.start()]
            for neighbor_idx in (idx - 1, idx + 1):
                neighbor_id = f"{prefix}:p{page}:c{neighbor_idx}"
                if neighbor_id in seen:
                    continue
                chunk = chunk_by_id.get(neighbor_id)
                if chunk is None or chunk.source != hit.chunk.source:
                    continue
                seen.add(neighbor_id)
                extras += 1
                out.append(
                    SearchHit(
                        chunk=chunk,
                        score=float(hit.score) * 0.5,
                        explanation={
                            "dense_score": None,
                            "bm25_score": None,
                            "rerank_score": None,
                            "related_to": hit.chunk.chunk_id,
                            "final_rank_reason": "adjacent chunk added for multi-hop context",
                        },
                    )
                )
                if extras >= max_extra:
                    return out
        return out

    def _compress_candidates(
        self,
        *,
        query: str,
        intent: str,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        normalizer = BM25TextNormalizer(self.settings.retrieval.bm25)
        query_terms = set(normalizer.tokenize(query))
        if intent in {"count", "list"}:
            max_sentences = 10
            max_chars = 3200
        elif intent == "summary":
            max_sentences = 12
            max_chars = 4500
        else:
            max_sentences = 4
            max_chars = 1400
        seen_text: set[str] = set()
        compressed: list[SearchHit] = []
        for hit in hits:
            normalized_text = " ".join(hit.chunk.text.lower().split())
            if normalized_text in seen_text:
                continue
            seen_text.add(normalized_text)
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+|\n+", hit.chunk.text)
                if s.strip()
            ]
            ranked_sentences: list[tuple[int, int, str]] = []
            matched_keywords: set[str] = set()
            for idx, sentence in enumerate(sentences):
                terms = set(normalizer.tokenize(sentence))
                overlap = len(query_terms & terms)
                matched_keywords.update(query_terms & terms)
                ranked_sentences.append((overlap, -idx, sentence))
            selected = [
                item[2]
                for item in sorted(ranked_sentences, reverse=True)
                if item[0] > 0
            ][:max_sentences]
            if not selected:
                selected = sentences[:max_sentences] if sentences else [hit.chunk.text]
            elif intent in {"count", "list"}:
                # Preserve nearby list structure after the first matched sentence; count/list
                # questions often need adjacent entities that do not repeat the query words.
                selected_set = set(selected)
                for _, neg_idx, _ in sorted(ranked_sentences, reverse=True):
                    idx = -neg_idx
                    for neighbor in (idx - 1, idx + 1):
                        if 0 <= neighbor < len(sentences) and sentences[neighbor] not in selected_set:
                            selected.append(sentences[neighbor])
                            selected_set.add(sentences[neighbor])
                            if len(selected) >= max_sentences:
                                break
                    if len(selected) >= max_sentences:
                        break
            text = " ".join(selected).strip()
            if len(text) > max_chars:
                text = text[:max_chars].rsplit(" ", 1)[0].strip()
            chunk = IndexedChunk(
                chunk_id=hit.chunk.chunk_id,
                source=hit.chunk.source,
                page=hit.chunk.page,
                text=text or hit.chunk.text[:max_chars],
                metadata={**hit.chunk.metadata, "original_chars": len(hit.chunk.text)},
            )
            compressed.append(
                SearchHit(
                    chunk=chunk,
                    score=hit.score,
                    explanation={
                        **hit.explanation,
                        "compressed": True,
                        "original_chars": len(hit.chunk.text),
                        "compressed_chars": len(chunk.text),
                        "matched_keywords": sorted(matched_keywords),
                        "selection_reason": (
                            f"selected because it matched query terms {sorted(matched_keywords)}"
                            if matched_keywords
                            else "selected by dense semantic retrieval and preserved for context"
                        ),
                        "semantic_similarity_explanation": (
                            "dense vector similarity contributed to selection"
                            if hit.explanation.get("dense_score") is not None
                            else "no dense score available; lexical or related-context candidate"
                        ),
                    },
                )
            )
        return compressed

    def _rerank_hits(
        self,
        *,
        query: str,
        hits: list[SearchHit],
        top_k: int,
        debug: dict[str, Any],
        mode: RetrievalMode,
    ) -> list[SearchHit]:
        if not hits:
            return hits
        rerank_started = time.perf_counter()
        rr = build_reranker_from_config(self.settings.retrieval.rerank)
        reranked = rr.rerank(
            query,
            [h.chunk.text for h in hits],
            base_scores=[float(h.score) for h in hits],
            top_k=top_k,
        )
        debug["timings_ms"]["rerank"] = round((time.perf_counter() - rerank_started) * 1000.0, 2)
        out = [
            SearchHit(
                chunk=hits[r.idx].chunk,
                score=float(r.score),
                explanation={
                    **hits[r.idx].explanation,
                    "rerank_score": float(r.score),
                    "rerank_rank": rank,
                    "final_rank_reason": (
                        "final order from reranker after compressed hybrid candidate set"
                    ),
                },
            )
            for rank, r in enumerate(reranked, start=1)
        ]
        rerank_top_scores = [
            round(float(h.score), 6) for h in out[: self.settings.retrieval.debug_top_n]
        ]
        log.info(
            "retrieval.rerank_hits",
            mode=mode,
            num_hits=len(out),
            top_scores=rerank_top_scores,
        )
        debug["stage_counts"]["rerank_hits"] = len(out)
        debug["top_scores"]["rerank"] = rerank_top_scores
        debug["top_ids"]["rerank"] = [
            h.chunk.chunk_id for h in out[: self.settings.retrieval.debug_top_n]
        ]
        return out

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
        if mode == "dense":
            log.warning("retrieval.mode_dense_requested", message="Production path should use hybrid.")

        do_rewrite = (
            self.settings.retrieval.query_rewrite.enabled
            if rewrite_override is None
            else rewrite_override
        )
        plan = build_query_plan(
            self.settings,
            self.rewrite_client,
            question,
            rewrite_enabled=bool(do_rewrite),
        )
        cache_key = (
            mode,
            plan.semantic_query,
            plan.lexical_query,
            plan.intent,
            plan.reasoning_hops,
            plan.sub_queries,
            int(top_k),
            filter_source_substr or "",
            bool(do_rewrite),
            self.settings.retrieval.rerank.provider,
            self.settings.retrieval.rerank.model_name,
            self._cache_identity(),
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        output = self._retrieve_with_fallback(
            plan=plan,
            question=question,
            top_k=top_k,
            filter_source_substr=filter_source_substr,
            mode=mode,
        )
        self._set_cached(cache_key, output)
        return output

    def _retrieve_with_fallback(
        self,
        *,
        plan: QueryPlan,
        question: str,
        top_k: int,
        filter_source_substr: str | None,
        mode: RetrievalMode,
    ) -> RetrievalOutput:
        primary = self._retrieve_once(
            plan=plan,
            question=question,
            top_k=top_k,
            filter_source_substr=filter_source_substr,
            mode=mode,
            attempt="primary",
        )
        primary = self._augment_with_multi_hop(
            primary=primary,
            plan=plan,
            question=question,
            top_k=top_k,
            filter_source_substr=filter_source_substr,
            mode=mode,
        )
        if primary.hits:
            return primary

        fallback_debug: dict[str, Any] = {"primary": primary.debug}
        if plan.rewrite_applied:
            raw_plan = QueryPlan(
                intent=plan.intent,
                semantic_query=question,
                lexical_query=question,
                rewrite_applied=False,
                reasoning_hops=1,
                sub_queries=(),
                required_facts=plan.required_facts,
            )
            raw_retry = self._retrieve_once(
                plan=raw_plan,
                question=question,
                top_k=top_k,
                filter_source_substr=filter_source_substr,
                mode=mode,
                attempt="retry_without_rewrite",
            )
            fallback_debug["retry_without_rewrite_hits"] = len(raw_retry.hits)
            if raw_retry.hits:
                debug = raw_retry.debug or {}
                debug["fallback_origin"] = fallback_debug
                debug["fallback_strategy"] = "retry_without_rewrite"
                return raw_retry

        bm25_plan = QueryPlan(
            intent=plan.intent,
            semantic_query=question,
            lexical_query=question,
            rewrite_applied=False,
            reasoning_hops=1,
            sub_queries=(),
            required_facts=plan.required_facts,
        )
        bm25_retry = self._retrieve_once(
            plan=bm25_plan,
            question=question,
            top_k=top_k,
            filter_source_substr=filter_source_substr,
            mode="bm25",
            attempt="fallback_bm25",
        )
        fallback_debug["fallback_bm25_hits"] = len(bm25_retry.hits)
        if bm25_retry.hits:
            debug = bm25_retry.debug or {}
            debug["fallback_origin"] = fallback_debug
            debug["fallback_strategy"] = "fallback_bm25"
            return bm25_retry

        debug = primary.debug or {}
        debug["fallback_attempted"] = fallback_debug
        debug["fallback_strategy"] = "no_sufficient_context"
        return RetrievalOutput(
            query_used=plan.semantic_query,
            hits=[],
            embedding_tokens=primary.embedding_tokens,
            embedding_cost_usd=primary.embedding_cost_usd,
            debug=debug,
        )

    def _augment_with_multi_hop(
        self,
        *,
        primary: RetrievalOutput,
        plan: QueryPlan,
        question: str,
        top_k: int,
        filter_source_substr: str | None,
        mode: RetrievalMode,
    ) -> RetrievalOutput:
        if plan.reasoning_hops <= 1 or not plan.sub_queries:
            debug = primary.debug or {}
            debug["multi_hop"] = {
                "enabled": bool(self.settings.retrieval.multi_hop_planning.enabled),
                "reasoning_hops": int(plan.reasoning_hops),
                "sub_queries": list(plan.sub_queries),
                "required_facts": list(plan.required_facts),
                "executed": False,
            }
            primary.debug = debug
            return primary

        merged: dict[str, SearchHit] = {h.chunk.chunk_id: h for h in primary.hits}
        hop_summaries: list[dict[str, Any]] = []
        total_embedding_tokens = int(primary.embedding_tokens)
        total_embedding_cost = float(primary.embedding_cost_usd)
        for hop_idx, sub_query in enumerate(plan.sub_queries, start=2):
            hop_plan = QueryPlan(
                intent=plan.intent,
                semantic_query=sub_query,
                lexical_query=sub_query,
                rewrite_applied=False,
                reasoning_hops=1,
                sub_queries=(),
                required_facts=plan.required_facts,
            )
            hop_output = self._retrieve_once(
                plan=hop_plan,
                question=question,
                top_k=max(2, min(int(top_k), 4)),
                filter_source_substr=filter_source_substr,
                mode=mode,
                attempt=f"multi_hop_{hop_idx}",
            )
            total_embedding_tokens += int(hop_output.embedding_tokens)
            total_embedding_cost += float(hop_output.embedding_cost_usd)
            hop_summaries.append(
                {
                    "hop": hop_idx,
                    "query": sub_query,
                    "num_hits": len(hop_output.hits),
                    "top_ids": [h.chunk.chunk_id for h in hop_output.hits[:3]],
                }
            )
            for hit in hop_output.hits:
                existing = merged.get(hit.chunk.chunk_id)
                if existing is None or float(hit.score) > float(existing.score):
                    merged[hit.chunk.chunk_id] = SearchHit(
                        chunk=hit.chunk,
                        score=hit.score,
                        explanation={
                            **(hit.explanation or {}),
                            "multi_hop_query": sub_query,
                            "multi_hop_hop": hop_idx,
                            "final_rank_reason": "selected by adaptive multi-hop retrieval planner",
                        },
                    )

        hits = sorted(merged.values(), key=lambda h: float(h.score), reverse=True)[:top_k]
        debug = primary.debug or {}
        debug["multi_hop"] = {
            "enabled": True,
            "reasoning_hops": int(plan.reasoning_hops),
            "sub_queries": list(plan.sub_queries),
            "required_facts": list(plan.required_facts),
            "executed": True,
            "hop_summaries": hop_summaries,
            "merged_candidate_count": len(merged),
        }
        debug.setdefault("stage_counts", {})["multi_hop_merged_hits"] = len(hits)
        debug.setdefault("top_ids", {})["multi_hop_final"] = [
            h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]
        ]
        return RetrievalOutput(
            query_used=primary.query_used,
            hits=hits,
            embedding_tokens=total_embedding_tokens,
            embedding_cost_usd=total_embedding_cost,
            debug=debug,
        )

    def _retrieve_once(
        self,
        *,
        plan: QueryPlan,
        question: str,
        top_k: int,
        filter_source_substr: str | None,
        mode: RetrievalMode,
        attempt: str,
    ) -> RetrievalOutput:
        debug: dict[str, Any] = {
            "mode": mode,
            "attempt": attempt,
            "question": question,
            "query_used": plan.semantic_query,
            "semantic_query": plan.semantic_query,
            "lexical_query": plan.lexical_query,
            "query_intent": plan.intent,
            "rewrite_applied": bool(plan.rewrite_applied),
            "reasoning_hops": int(plan.reasoning_hops),
            "sub_queries": list(plan.sub_queries),
            "required_facts": list(plan.required_facts),
            "index_identity": self._cache_identity(),
            "top_k_requested": int(top_k),
            "threshold_min_score": float(self.settings.retrieval.min_score),
            "stage_counts": {},
            "top_scores": {},
            "top_ids": {},
            "timings_ms": {},
        }
        log.info(
            "retrieval.query_rewrite",
            mode=mode,
            rewrite_applied=bool(plan.rewrite_applied),
            semantic_query=plan.semantic_query,
            lexical_query=plan.lexical_query,
            query_intent=plan.intent,
        )

        if mode == "bm25":
            bm25_started = time.perf_counter()
            hits = self._bm25_only_hits(
                plan.lexical_query, top_k=int(top_k), filter_source_substr=filter_source_substr
            )
            debug["timings_ms"]["bm25"] = round((time.perf_counter() - bm25_started) * 1000.0, 2)
            debug["stage_counts"] = {"bm25_hits": len(hits)}
            debug["top_scores"] = {
                "bm25": [
                    round(float(h.score), 6)
                    for h in hits[: self.settings.retrieval.debug_top_n]
                ]
            }
            debug["top_ids"] = {
                "bm25": [h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]]
            }
            compress_started = time.perf_counter()
            hits = self._compress_candidates(
                query=plan.semantic_query,
                intent=plan.intent,
                hits=hits,
            )
            debug["timings_ms"]["compression"] = round(
                (time.perf_counter() - compress_started) * 1000.0, 2
            )
            debug["stage_counts"]["compressed_hits"] = len(hits)
            hits = self._rerank_hits(
                query=plan.semantic_query,
                hits=hits,
                top_k=top_k,
                debug=debug,
                mode=mode,
            )
            hits, threshold_applied = self._apply_min_score_cutoff(
                hits, float(self.settings.retrieval.min_score)
            )
            top_scores = [
                round(float(h.score), 6) for h in hits[: self.settings.retrieval.debug_top_n]
            ]
            debug["stage_counts"]["final_hits"] = len(hits)
            debug["top_scores"]["final"] = top_scores
            debug["top_ids"]["final"] = [
                h.chunk.chunk_id for h in hits[: self.settings.retrieval.debug_top_n]
            ]
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
                query_used=plan.lexical_query,
                hits=hits,
                embedding_tokens=0,
                embedding_cost_usd=0.0,
                debug=debug,
            )
            return output

        # Dense retrieval always happens (we need embeddings anyway to answer). We can still reduce
        # dense candidates in hybrid if you want, but in practice a slightly larger dense_k improves stability.
        dense_started = time.perf_counter()
        emb = self.embedder.embed_query(plan.semantic_query)
        q_vec = emb.vectors[0]

        dense_k = int(self.settings.retrieval.hybrid.dense_k) if mode == "hybrid" else int(top_k)
        dense_k = max(int(top_k), dense_k)
        dense_hits = self.store.search(
            q_vec, top_k=dense_k, filter_source_substr=filter_source_substr
        )
        dense_hits = [
            SearchHit(
                chunk=h.chunk,
                score=h.score,
                explanation={
                    **h.explanation,
                    "dense_score": float(h.score),
                    "dense_rank": rank,
                    "bm25_score": None,
                    "final_rank_reason": "dense semantic candidate",
                },
            )
            for rank, h in enumerate(dense_hits, start=1)
        ]
        debug["timings_ms"]["dense"] = round((time.perf_counter() - dense_started) * 1000.0, 2)
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
            sparse_started = time.perf_counter()
            sparse_hits = bm25.query(
                plan.lexical_query,
                top_k=max(int(top_k), sparse_k),
                filter_fn=_filter_fn,
            )
            sparse_hits = [
                hit
                for hit in sparse_hits
                if float(hit.score) >= float(self.settings.retrieval.hybrid.min_sparse_score)
            ]
            debug["timings_ms"]["bm25"] = round((time.perf_counter() - sparse_started) * 1000.0, 2)
            sparse_top_scores = [
                round(float(h.score), 6)
                for h in sparse_hits[: self.settings.retrieval.debug_top_n]
            ]
            log.info(
                "retrieval.bm25_hits",
                mode=mode,
                bm25_k=sparse_k,
                num_hits=len(sparse_hits),
                top_scores=sparse_top_scores,
            )

            fusion_started = time.perf_counter()
            hits, fusion_debug = self._fuse_dense_and_sparse(
                dense_hits=dense_hits,
                sparse_hits=sparse_hits,
                chunk_by_id=chunk_by_id,
                top_k=top_k,
            )
            hits = self._expand_related_chunks(
                hits,
                chunk_by_id,
                max_extra=max(0, min(int(top_k), 4)),
            )
            debug["timings_ms"]["fusion"] = round(
                (time.perf_counter() - fusion_started) * 1000.0, 2
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

        compress_started = time.perf_counter()
        hits = self._compress_candidates(
            query=plan.semantic_query,
            intent=plan.intent,
            hits=hits,
        )
        debug["timings_ms"]["compression"] = round(
            (time.perf_counter() - compress_started) * 1000.0, 2
        )
        debug["stage_counts"]["compressed_hits"] = len(hits)

        # Reranker always runs after fusion/dense/BM25 when candidates exist.
        hits = self._rerank_hits(
            query=plan.semantic_query,
            hits=hits,
            top_k=top_k,
            debug=debug,
            mode=mode,
        )

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
            query_used=plan.semantic_query,
            hits=hits,
            embedding_tokens=emb.total_tokens,
            embedding_cost_usd=emb.cost_usd,
            debug=debug,
        )
        return output
