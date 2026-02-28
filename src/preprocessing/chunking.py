from __future__ import annotations

from dataclasses import dataclass

import tiktoken

from utils.settings import ChunkingConfig


@dataclass(frozen=True)
class TextChunk:
    idx: int
    text: str


class TokenChunker:
    def __init__(self, cfg: ChunkingConfig, encoding_name: str = "cl100k_base") -> None:
        self.cfg = cfg
        # tiktoken downloads some encodings on first use; in locked-down environments
        # (CI, air-gapped) that can fail. We fall back to a whitespace tokenizer so
        # the pipeline remains runnable (and tests don't require network).
        self.enc = None
        try:
            self.enc = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.enc = None

    def split(self, text: str) -> list[TextChunk]:
        if not text:
            return []
        if self.enc is not None:
            tokens = self.enc.encode(text)
            decode = lambda toks: self.enc.decode(toks)
        else:
            tokens = text.split()
            decode = lambda toks: " ".join(toks)
        size = self.cfg.chunk_size
        overlap = self.cfg.chunk_overlap
        out: list[TextChunk] = []
        start = 0
        idx = 0
        while start < len(tokens):
            end = min(start + size, len(tokens))
            chunk_text = decode(tokens[start:end]).strip()
            if chunk_text:
                out.append(TextChunk(idx=idx, text=chunk_text))
                idx += 1
            if end >= len(tokens):
                break
            start = max(0, end - overlap)
        return out


class CharChunker:
    def __init__(self, cfg: ChunkingConfig) -> None:
        self.cfg = cfg

    def split(self, text: str) -> list[TextChunk]:
        size = self.cfg.max_chars_fallback
        overlap = min(self.cfg.chunk_overlap, size // 2)
        out: list[TextChunk] = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                out.append(TextChunk(idx=idx, text=chunk))
                idx += 1
            if end >= len(text):
                break
            start = max(0, end - overlap)
        return out


def chunk_text(text: str, cfg: ChunkingConfig) -> list[TextChunk]:
    if cfg.strategy == "token":
        return TokenChunker(cfg).split(text)
    return CharChunker(cfg).split(text)
