from __future__ import annotations

from pathlib import Path

from embeddings.factory import build_embeddings_backend
from retrieval.bm25 import BM25PersistentIndex
from retrieval.corpus import load_chunks_jsonl
from retrieval.vector_store import VectorStore, build_vector_store
from utils.config import ensure_dirs, load_settings
from utils.logging import configure_logging, get_logger

log = get_logger(__name__)


def build_index_main() -> None:
    settings = load_settings()
    ensure_dirs(settings)
    configure_logging()

    chunks_path = Path(settings.paths.chunks_dir) / "chunks.jsonl"
    if not chunks_path.exists():
        raise FileNotFoundError("Missing chunks.jsonl. Run scripts/ingest_data.py first.")

    chunks, _ = load_chunks_jsonl(str(chunks_path))
    log.info("index.read_chunks", num_chunks=len(chunks))

    # Build BM25 over the *full* corpus (required for hybrid retrieval).
    # This is a local, reproducible baseline. Large deployments should swap this for Lucene/ES.
    bm25_dir = Path(settings.paths.indexes_dir) / "bm25"
    texts_by_id: dict[str, str] = {c.chunk_id: c.text for c in chunks}
    BM25PersistentIndex.build(texts_by_id).save(str(bm25_dir))
    log.info("index.bm25_saved", dir=str(bm25_dir), num_docs=len(texts_by_id))

    embedder = build_embeddings_backend(settings)
    store: VectorStore = build_vector_store(settings)

    batch = int(settings.embeddings.batch_size)
    total_cost = 0.0
    total_tokens = 0

    for i in range(0, len(chunks), batch):
        b = chunks[i : i + batch]
        texts = [c.text for c in b]
        emb = embedder.embed_texts(texts)
        store.add(b, emb.vectors)
        total_tokens += emb.total_tokens
        total_cost += emb.cost_usd
        log.info(
            "index.batch", start=i, size=len(b), tokens=emb.total_tokens, cost_usd=emb.cost_usd
        )

    store.save()
    log.info(
        "index.saved",
        provider=settings.vector_store.provider,
        total_tokens=total_tokens,
        total_cost_usd=total_cost,
    )


if __name__ == "__main__":
    build_index_main()
