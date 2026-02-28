from __future__ import annotations

from embeddings.base import EmbeddingsBackend, EmbedResult
from utils.openai_client import OpenAIClient
from utils.settings import EmbeddingsConfig


class OpenAIEmbeddingsBackend(EmbeddingsBackend):
    def __init__(self, cfg: EmbeddingsConfig) -> None:
        oai = cfg.openai
        self.model = cfg.model
        self.usd_per_1k = float(oai.usd_per_1k_tokens or 0.0)
        self.client = OpenAIClient(
            api_key=oai.api_key,
            base_url=oai.base_url,
            organization=oai.organization,
            timeout_s=oai.request_timeout_s,
            max_retries=oai.max_retries,
        )

    def _cost(self, tokens: int) -> float:
        return (tokens / 1000.0) * self.usd_per_1k

    def embed_texts(self, texts: list[str]) -> EmbedResult:
        vectors, usage = self.client.embed(self.model, texts)
        return EmbedResult(
            vectors=vectors,
            total_tokens=usage.total_tokens,
            cost_usd=self._cost(usage.total_tokens),
        )

    def embed_query(self, text: str) -> EmbedResult:
        return self.embed_texts([text])
