from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    total_tokens: int = 0
    cost_usd: float = 0.0


class EmbeddingsBackend(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> EmbedResult:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> EmbedResult:
        raise NotImplementedError
