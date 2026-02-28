from __future__ import annotations

from embeddings.base import EmbeddingsBackend
from embeddings.openai_embeddings import OpenAIEmbeddingsBackend
from utils.settings import Settings


def build_embeddings_backend(settings: Settings) -> EmbeddingsBackend:
    if settings.embeddings.provider == "openai":
        return OpenAIEmbeddingsBackend(settings.embeddings)
    if settings.embeddings.provider == "sentence_transformers":
        # Optional dependency: do not import unless configured.
        try:
            from embeddings.sentence_transformers_embeddings import (
                SentenceTransformersEmbeddingsBackend,
            )
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "sentence-transformers is not installed. Install it or switch embeddings.provider to 'openai'."
            ) from e
        return SentenceTransformersEmbeddingsBackend(settings.embeddings)
    raise ValueError(f"Unknown embeddings provider: {settings.embeddings.provider}")
