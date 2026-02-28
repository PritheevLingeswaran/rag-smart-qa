from __future__ import annotations

import json
from pathlib import Path

from retrieval.vector_store import IndexedChunk


def load_chunks_jsonl(path: str) -> tuple[list[IndexedChunk], dict[str, IndexedChunk]]:
    """Load the canonical chunk corpus.

    Why this helper exists:
    - Dense stores (e.g., Chroma) can return documents without us holding the full corpus in memory.
    - Sparse retrieval (BM25) needs access to the *full* document list to return chunks that were not
      included in the dense top-k.
    - We keep this in a single place so build scripts + API code use consistent parsing.
    """

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Missing chunks corpus at {path}. Run scripts/ingest_data.py first."
        )

    chunks: list[IndexedChunk] = []
    by_id: dict[str, IndexedChunk] = {}

    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            c = IndexedChunk(
                chunk_id=obj["chunk_id"],
                source=obj["source"],
                page=int(obj.get("page", 0)),
                text=obj["text"],
                metadata=obj.get("metadata", {}) or {},
            )
            chunks.append(c)
            by_id[c.chunk_id] = c

    return chunks, by_id
