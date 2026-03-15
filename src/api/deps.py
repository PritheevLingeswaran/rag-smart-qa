from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import cast

from fastapi import Depends, Request

from generation.answerer import Answerer
from retrieval.retriever import Retriever
from retrieval.vector_store import (
    ChromaVectorStore,
    FaissVectorStore,
    VectorStore,
    build_vector_store,
)
from services.auth_service import AuthService
from services.chat_service import ChatService
from services.document_service import DocumentService
from services.metadata_service import MetadataService
from services.storage_service import LocalStorageService, StorageService
from services.summary_service import SummaryService
from utils.config import ensure_dirs, load_settings
from utils.logging import configure_logging
from utils.settings import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = load_settings()
    ensure_dirs(settings)
    configure_logging()
    return settings


@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    settings = get_settings()
    if settings.vector_store.provider == "chroma":
        return ChromaVectorStore.load(settings)
    if settings.vector_store.provider == "faiss":
        return FaissVectorStore.load(settings)
    return build_vector_store(settings)


def get_vector_count(store: VectorStore) -> int:
    if hasattr(store, "_collection"):
        try:
            return int(store._collection.count())  # type: ignore[attr-defined]
        except Exception:
            return 0
    if hasattr(store, "index") and getattr(store, "index", None) is not None:
        try:
            return int(store.index.ntotal)  # type: ignore[attr-defined]
        except Exception:
            return 0
    return 0


def validate_runtime_readiness() -> None:
    settings = get_settings()
    chunks_path = Path(settings.paths.chunks_dir) / "chunks.jsonl"
    if not chunks_path.exists():
        raise RuntimeError(f"Missing chunks file at {chunks_path}. Run ingest + build_index first.")

    chunks_count = 0
    with chunks_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks_count += 1
    if chunks_count == 0:
        raise RuntimeError(
            f"Empty chunks file at {chunks_path}. Run ingest_data to rebuild chunks."
        )

    bm25_dir = Path(settings.paths.indexes_dir) / "bm25"
    if not (bm25_dir / "bm25.pkl").exists():
        raise RuntimeError(f"Missing BM25 index at {bm25_dir}. Run build_index.")

    store = get_store()
    vector_count = get_vector_count(store)
    if vector_count == 0:
        raise RuntimeError(
            "Vector store is empty. Run build_index and verify vector_store paths/config."
        )


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever(get_settings(), get_store())


@lru_cache(maxsize=1)
def get_answerer() -> Answerer:
    return Answerer(get_settings())


@lru_cache(maxsize=1)
def get_metadata_service() -> MetadataService:
    return MetadataService(get_settings())


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return LocalStorageService(get_settings())


@lru_cache(maxsize=1)
def get_summary_service() -> SummaryService:
    return SummaryService(get_settings())


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    return DocumentService(
        get_settings(),
        get_metadata_service(),
        get_storage_service(),
        get_summary_service(),
    )


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    return ChatService(get_settings(), get_metadata_service(), get_document_service())


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService(get_settings())


def get_current_user_id(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> str:
    settings = get_settings()
    header_value = request.headers.get(settings.auth.header_user_id)
    return cast(str, auth_service.resolve_user_id(header_value))
