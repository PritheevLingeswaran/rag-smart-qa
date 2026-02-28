from __future__ import annotations

from sentence_transformers import SentenceTransformer

from embeddings.base import EmbeddingsBackend, EmbedResult
from utils.settings import EmbeddingsConfig


class SentenceTransformersEmbeddingsBackend(EmbeddingsBackend):
    def __init__(self, cfg: EmbeddingsConfig) -> None:
        self.model = SentenceTransformer(cfg.sentence_transformers.model_name)

    def embed_texts(self, texts: list[str]) -> EmbedResult:
        vecs = self.model.encode(texts, convert_to_numpy=False, normalize_embeddings=True)
        return EmbedResult(vectors=[list(v) for v in vecs], total_tokens=0, cost_usd=0.0)

    def embed_query(self, text: str) -> EmbedResult:
        return self.embed_texts([text])
