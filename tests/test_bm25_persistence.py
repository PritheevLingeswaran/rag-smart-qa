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
