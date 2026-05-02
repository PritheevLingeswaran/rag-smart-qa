from __future__ import annotations

from measure_production_metrics import extract_doc_ids
from retrieval.bm25 import BM25DocHit
from retrieval.retriever import Retriever
from retrieval.vector_store import IndexedChunk, SearchHit
from utils.settings import Settings


def _chunk(cid: str, source: str = "doc.txt") -> IndexedChunk:
    return IndexedChunk(chunk_id=cid, source=source, page=1, text=f"text-{cid}", metadata={})


def test_extract_doc_ids_from_sources_and_ids() -> None:
    assert extract_doc_ids({"ids": ["a", "b"]}) == ["a", "b"]
    assert extract_doc_ids({"sources": [{"doc_id": "d1"}, {"id": "d2"}, {"source_id": "d3"}]}) == [
        "d1",
        "d2",
        "d3",
    ]
    assert extract_doc_ids({"retrieved": [{"doc_id": "x"}]}) == ["x"]


def test_apply_min_score_cutoff_falls_back_to_unfiltered_when_all_removed() -> None:
    hits = [
        SearchHit(chunk=_chunk("c1"), score=0.1),
        SearchHit(chunk=_chunk("c2"), score=0.08),
    ]
    out, threshold_applied = Retriever._apply_min_score_cutoff(hits, min_score=0.2)
    assert threshold_applied is False
    assert [h.chunk.chunk_id for h in out] == ["c1", "c2"]


def test_fusion_uses_rrf_only_and_unions_candidates() -> None:
    settings = Settings()
    settings.retrieval.hybrid.rrf_k = 10
    retriever = Retriever.__new__(Retriever)
    retriever.settings = settings

    dense_hits = [
        SearchHit(chunk=_chunk("a"), score=0.9),
        SearchHit(chunk=_chunk("b"), score=0.2),
    ]
    sparse_hits = [
        BM25DocHit(idx=0, chunk_id="b", score=8.0),
        BM25DocHit(idx=1, chunk_id="c", score=4.0),
    ]
    chunk_by_id = {"a": _chunk("a"), "b": _chunk("b"), "c": _chunk("c")}

    fused, debug = retriever._fuse_dense_and_sparse(
        dense_hits=dense_hits,
        sparse_hits=sparse_hits,
        chunk_by_id=chunk_by_id,
        top_k=3,
    )
    assert [h.chunk.chunk_id for h in fused] == ["b", "a", "c"]
    assert debug["fusion_method"] == "rrf"
    assert debug["candidate_count"] == 3


def test_rrf_fusion_can_promote_sparse_hit_without_dense_score() -> None:
    settings = Settings()
    settings.retrieval.hybrid.fusion_method = "rrf"
    settings.retrieval.hybrid.rrf_k = 10
    retriever = Retriever.__new__(Retriever)
    retriever.settings = settings

    dense_hits = [
        SearchHit(chunk=_chunk("a"), score=0.9),
        SearchHit(chunk=_chunk("b"), score=0.8),
    ]
    sparse_hits = [
        BM25DocHit(idx=0, chunk_id="c", score=8.0),
        BM25DocHit(idx=1, chunk_id="b", score=7.5),
    ]
    chunk_by_id = {"a": _chunk("a"), "b": _chunk("b"), "c": _chunk("c")}

    fused, debug = retriever._fuse_dense_and_sparse(
        dense_hits=dense_hits,
        sparse_hits=sparse_hits,
        chunk_by_id=chunk_by_id,
        top_k=3,
    )

    assert debug["fusion_method"] == "rrf"
    assert "c" in [h.chunk.chunk_id for h in fused]
    sparse_only = next(h for h in fused if h.chunk.chunk_id == "c")
    assert sparse_only.explanation["dense_score"] is None
    assert sparse_only.explanation["bm25_score"] == 8.0
    assert "reciprocal rank fusion" in sparse_only.explanation["final_rank_reason"]


def test_adaptive_count_compression_preserves_entities_and_explains_selection() -> None:
    settings = Settings()
    retriever = Retriever.__new__(Retriever)
    retriever.settings = settings
    hit = SearchHit(
        chunk=IndexedChunk(
            chunk_id="resume:p1:c0",
            source="resume.txt",
            page=1,
            text=(
                "Projects\n"
                "Production-Grade Hybrid RAG System (rag-smart-qa)\n"
                "Production-Grade Real-Time ML Drift Detection System (realtime-ml-drift)\n"
                "Production-Grade ML Decision Platform (ml-decision-platform)\n"
            ),
            metadata={},
        ),
        score=0.8,
        explanation={"dense_score": 0.8},
    )

    compressed = retriever._compress_candidates(
        query="How many projects are there?",
        intent="count",
        hits=[hit],
    )

    assert "rag-smart-qa" in compressed[0].chunk.text
    assert "realtime-ml-drift" in compressed[0].chunk.text
    assert compressed[0].explanation["matched_keywords"]
    assert "selected because" in compressed[0].explanation["selection_reason"]
