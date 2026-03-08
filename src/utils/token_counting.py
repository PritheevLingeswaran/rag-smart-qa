from __future__ import annotations

from functools import lru_cache

import tiktoken
from tiktoken.core import Encoding


@lru_cache(maxsize=8)
def _encoding_for_model(model: str) -> Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def estimate_text_tokens(text: str, model: str = "cl100k_base") -> int:
    encoding = _encoding_for_model(model)
    return len(encoding.encode(text or ""))


def estimate_batch_tokens(texts: list[str], model: str = "cl100k_base") -> int:
    return sum(estimate_text_tokens(text, model=model) for text in texts)


def estimate_chat_tokens(messages: list[dict[str, object]], model: str = "cl100k_base") -> int:
    total = 0
    for message in messages:
        total += 4
        total += estimate_text_tokens(str(message.get("role", "")), model=model)
        total += estimate_text_tokens(str(message.get("content", "")), model=model)
    total += 2
    return total
