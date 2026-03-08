from __future__ import annotations

from sentence_transformers import SentenceTransformer

from embeddings.base import EmbeddingsBackend, EmbedResult
from utils.settings import EmbeddingsConfig
from utils.token_counting import estimate_batch_tokens


class SentenceTransformersEmbeddingsBackend(EmbeddingsBackend):
    def __init__(self, cfg: EmbeddingsConfig) -> None:
        model_name = cfg.sentence_transformers.model_name or cfg.model
        try:
            self.model = SentenceTransformer(
                model_name,
                local_files_only=cfg.sentence_transformers.local_files_only,
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to load sentence-transformers model "
                f"'{model_name}'. If this is the first run, ensure internet access to "
                "huggingface.co so the model can be downloaded, or set "
                "'embeddings.provider: openai'. To force offline mode, set "
                "'embeddings.sentence_transformers.local_files_only: true' and use a cached model."
            ) from e

    def embed_texts(self, texts: list[str]) -> EmbedResult:
        vecs = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return EmbedResult(
            vectors=vecs.tolist(),
            total_tokens=estimate_batch_tokens(texts, model="cl100k_base"),
            cost_usd=0.0,
        )

    def embed_query(self, text: str) -> EmbedResult:
        return self.embed_texts([text])
