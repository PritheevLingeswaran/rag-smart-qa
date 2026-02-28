from __future__ import annotations

from functools import lru_cache

from generation.answerer import Answerer
from retrieval.retriever import Retriever
from retrieval.vector_store import (
    ChromaVectorStore,
    FaissVectorStore,
    VectorStore,
    build_vector_store,
)
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


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    return Retriever(get_settings(), get_store())


@lru_cache(maxsize=1)
def get_answerer() -> Answerer:
    return Answerer(get_settings())
