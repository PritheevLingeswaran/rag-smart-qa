from __future__ import annotations

from pathlib import Path

from retrieval.bm25 import BM25PersistentIndex


def test_bm25_persist_and_query(tmp_path: Path) -> None:
    texts = {
        "c1": "the quick brown fox jumps over the lazy dog",
        "c2": "vector databases store embeddings and enable similarity search",
        "c3": "bm25 is a sparse retrieval algorithm based on term frequency",
    }

    idx = BM25PersistentIndex.build(texts)
    idx.save(str(tmp_path))

    loaded = BM25PersistentIndex.load(str(tmp_path))
    hits = loaded.query("sparse term frequency", top_k=2)

    # The bm25-related chunk should win.
    assert hits
    assert hits[0].chunk_id == "c3"


def test_bm25_returns_no_hits_when_query_has_no_overlap() -> None:
    idx = BM25PersistentIndex.build({"c1": "alpha beta gamma"})

    assert idx.query("unrelated", top_k=3) == []


def test_bm25_structural_title_slide_query_can_find_author_slide() -> None:
    idx = BM25PersistentIndex.build(
        {
            "title": (
                "THE DEATH OF TRUST By Mathew Anu Joy (RA2411026010225) "
                "Pritheev Lingeswaran (RA2411026010228)"
            ),
            "body": "Deepfake risks and consequences include fraud and identity theft.",
            "conclusion": "The future of truth requires responsibility and technical safeguards.",
        }
    )

    hits = idx.query("how many names are there by ra", top_k=3)

    assert hits
    assert hits[0].chunk_id == "title"
