from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import numpy as np

from utils.settings import Settings


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    source: str
    page: int
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SearchHit:
    chunk: IndexedChunk
    score: float  # normalized similarity-like score in [0,1]


def _as_numpy_2d(vectors: Any) -> np.ndarray:
    """
    Convert embeddings into a 2D float32 numpy array on CPU.

    Supports:
      - list[list[float]]
      - np.ndarray
      - torch.Tensor (CPU/CUDA/MPS)
      - list[torch.Tensor]
    """
    # torch.Tensor or list[torch.Tensor] (including MPS/CUDA)
    if hasattr(vectors, "detach"):
        vectors = vectors.detach().cpu().numpy()
    elif isinstance(vectors, list) and vectors and hasattr(vectors[0], "detach"):
        vectors = np.stack([v.detach().cpu().numpy() for v in vectors], axis=0)
    elif (
        isinstance(vectors, list)
        and vectors
        and isinstance(vectors[0], list)
        and vectors[0]
        and hasattr(vectors[0][0], "detach")
    ):
        vectors = [[float(v.detach().cpu().item()) for v in row] for row in vectors]

    arr = np.asarray(vectors, dtype=np.float32)

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    elif arr.ndim != 2:
        raise ValueError(f"Embeddings must be 1D or 2D. Got shape {arr.shape} (ndim={arr.ndim}).")
    return arr


def _as_numpy_1d(vector: Any) -> np.ndarray:
    """
    Convert a single query vector into 1D float32 numpy array on CPU.
    Supports torch.Tensor (CPU/CUDA/MPS) and lists/np arrays.
    """
    if hasattr(vector, "detach"):
        vector = vector.detach().cpu().numpy()
    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
    return arr


def _to_float_matrix(vectors: Any) -> list[list[float]]:
    """Convert embeddings into Chroma-compatible List[List[float]]."""
    return cast(list[list[float]], _as_numpy_2d(vectors).tolist())


def _to_float_vector(vector: Any) -> list[float]:
    """Convert single query vector into List[float] for Chroma query."""
    return cast(list[float], _as_numpy_1d(vector).tolist())


def _safe_int(value: Any, default: int = 0) -> int:
    """Best-effort int coercion for external metadata values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[IndexedChunk], vectors: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query_vector: Any,
        top_k: int,
        filter_source_substr: str | None = None,
    ) -> list[SearchHit]:
        raise NotImplementedError

    @abstractmethod
    def save(self) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def load(cls, settings: Settings) -> VectorStore:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    def __init__(self, settings: Settings) -> None:
        chromadb = import_module("chromadb")

        self.settings = settings
        self.persist_dir = settings.vector_store.chroma.persist_dir
        self.collection_name = settings.vector_store.chroma.collection_name
        self._client = chromadb.PersistentClient(path=self.persist_dir)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)

    def add(self, chunks: list[IndexedChunk], vectors: Any) -> None:
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        docs = [c.text for c in chunks]
        metas = [{"source": c.source, "page": c.page, **(c.metadata or {})} for c in chunks]

        emb = _to_float_matrix(vectors)

        if len(emb) != len(chunks):
            raise ValueError(
                f"Embeddings count mismatch: got {len(emb)} vectors for {len(chunks)} chunks."
            )

        # Use upsert so repeated indexing refreshes existing IDs
        # instead of serving stale content from earlier runs.
        self._collection.upsert(
            ids=ids,
            documents=docs,
            embeddings=cast(Any, emb),
            metadatas=cast(Any, metas),
        )

    def search(
        self, query_vector: Any, top_k: int, filter_source_substr: str | None = None
    ) -> list[SearchHit]:
        q = _to_float_vector(query_vector)

        res = self._collection.query(
            query_embeddings=cast(Any, [q]),
            n_results=top_k * 5,
            include=["distances", "documents", "metadatas"],
        )

        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        hits: list[SearchHit] = []
        for cid, doc, metadata_obj, dist in zip(ids, docs, metas, dists, strict=False):
            metadata = metadata_obj or {}
            source = str(metadata.get("source", ""))

            if filter_source_substr and filter_source_substr not in source:
                continue

            score = 1.0 / (1.0 + float(dist))

            chunk = IndexedChunk(
                chunk_id=str(cid),
                source=source,
                page=_safe_int(metadata.get("page", 0), default=0),
                text=str(doc),
                metadata={k: v for k, v in metadata.items() if k not in {"source", "page"}},
            )
            hits.append(SearchHit(chunk=chunk, score=float(score)))
            if len(hits) >= top_k:
                break

        return hits

    def save(self) -> None:
        return

    @classmethod
    def load(cls, settings: Settings) -> ChromaVectorStore:
        return cls(settings)


class FaissVectorStore(VectorStore):
    def __init__(self, settings: Settings) -> None:
        try:
            faiss = import_module("faiss")
        except Exception as e:  # pragma: no cover
            raise ImportError(
                "faiss is not installed. Install faiss-cpu to use this backend."
            ) from e

        self._faiss = faiss
        self.settings = settings
        self.metric = settings.vector_store.faiss.metric
        self.normalize = settings.vector_store.faiss.normalize
        self.index: Any | None = None
        self.chunks: list[IndexedChunk] = []

        self.persist_dir = Path(settings.paths.indexes_dir) / "faiss"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    def _make_index(self, dim: int) -> Any:
        if self.metric == "cosine":
            return self._faiss.IndexFlatIP(dim)
        return self._faiss.IndexFlatL2(dim)

    def add(self, chunks: list[IndexedChunk], vectors: Any) -> None:
        if not chunks:
            return

        x = _as_numpy_2d(vectors)  # ✅ handles torch MPS/CUDA safely

        if self.metric == "cosine" and self.normalize:
            self._faiss.normalize_L2(x)

        if self.index is None:
            self.index = self._make_index(x.shape[1])

        assert self.index is not None
        self.index.add(x)
        self.chunks.extend(chunks)

    def search(
        self, query_vector: Any, top_k: int, filter_source_substr: str | None = None
    ) -> list[SearchHit]:
        if self.index is None:
            return []

        q = _as_numpy_1d(query_vector)
        q2 = np.asarray([q], dtype=np.float32)

        if self.metric == "cosine" and self.normalize:
            self._faiss.normalize_L2(q2)

        distances, indices = self.index.search(q2, top_k * 5)

        hits: list[SearchHit] = []
        for dist, idx in zip(distances[0].tolist(), indices[0].tolist(), strict=False):
            if idx < 0 or idx >= len(self.chunks):
                continue

            chunk = self.chunks[idx]
            if filter_source_substr and filter_source_substr not in chunk.source:
                continue

            if self.metric == "cosine":
                # IndexFlatIP returns inner product; with normalized vectors this
                # equals cosine similarity in [-1, 1].
                score = float(max(0.0, min(1.0, (dist + 1.0) / 2.0)))
            else:
                score = 1.0 / (1.0 + float(dist))

            hits.append(SearchHit(chunk=chunk, score=score))
            if len(hits) >= top_k:
                break

        return hits

    def save(self) -> None:
        if self.index is None:
            raise ValueError("Cannot save empty FAISS index.")
        self._faiss.write_index(self.index, str(self.persist_dir / "index.faiss"))
        with (self.persist_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c.__dict__, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, settings: Settings) -> FaissVectorStore:
        store = cls(settings)
        idx_path = store.persist_dir / "index.faiss"
        meta_path = store.persist_dir / "chunks.jsonl"
        if not idx_path.exists() or not meta_path.exists():
            raise FileNotFoundError("FAISS index missing. Run ingest + index first.")
        store.index = store._faiss.read_index(str(idx_path))
        store.chunks = []
        with meta_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                store.chunks.append(
                    IndexedChunk(
                        chunk_id=obj["chunk_id"],
                        source=obj["source"],
                        page=int(obj["page"]),
                        text=obj["text"],
                        metadata=obj.get("metadata", {}),
                    )
                )
        return store


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.vector_store.provider == "chroma":
        return ChromaVectorStore(settings)
    if settings.vector_store.provider == "faiss":
        return FaissVectorStore(settings)
    if settings.vector_store.provider == "pinecone":
        raise NotImplementedError("Pinecone is an extension point for your deployment.")
    raise ValueError(f"Unknown vector_store provider: {settings.vector_store.provider}")
