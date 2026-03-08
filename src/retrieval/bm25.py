from __future__ import annotations

import json
import pickle
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from utils.settings import BM25Config

_DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}
_EN_DASH = "\N{EN DASH}"


def _simple_stem(token: str) -> str:
    for suffix in ("ingly", "edly", "ing", "edly", "edly", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


class BM25TextNormalizer:
    def __init__(self, cfg: BM25Config | None = None) -> None:
        self.cfg = cfg or BM25Config()
        self._pattern = re.compile(r"[A-Za-z0-9]+")
        self._spaced_word_pattern = re.compile(r"\b(?:[A-Za-z0-9]\s+){2,}[A-Za-z0-9]\b")

    def normalize_text(self, text: str) -> str:
        # PDF extraction can yield letter-spaced words like "F a s t A P I".
        collapsed = self._spaced_word_pattern.sub(
            lambda match: re.sub(r"\s+", "", match.group(0)),
            text,
        )
        return collapsed.replace(_EN_DASH, "-")

    def tokenize(self, text: str) -> list[str]:
        text = self.normalize_text(text)
        tokens = self._pattern.findall(text) if self.cfg.strip_punctuation else text.split()
        out: list[str] = []
        for token in tokens:
            t = token.lower() if self.cfg.lowercase else token
            if len(t) < int(self.cfg.min_token_length):
                continue
            if self.cfg.remove_stopwords and t in _DEFAULT_STOPWORDS:
                continue
            if self.cfg.stemming:
                t = _simple_stem(t)
            if t:
                out.append(t)
        return out


@dataclass(frozen=True)
class BM25Hit:
    idx: int
    score: float


class BM25Index:
    def __init__(self, texts: list[str], cfg: BM25Config | None = None) -> None:
        self.texts = texts
        self._normalizer = BM25TextNormalizer(cfg)
        self.tokens = [self._normalizer.tokenize(t) for t in texts]
        self.bm25 = BM25Okapi(self.tokens)

    def query(self, q: str, top_k: int) -> list[BM25Hit]:
        scores = self.bm25.get_scores(self._normalizer.tokenize(q))
        ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)[:top_k]
        return [BM25Hit(idx=i, score=float(s)) for i, s in ranked]


# -----------------------------
# Persistent BM25 (full corpus)
# -----------------------------


@dataclass(frozen=True)
class BM25DocHit:
    idx: int
    chunk_id: str
    score: float


class BM25PersistentIndex:
    """A persistent BM25 index over the full chunk corpus.

    Why this exists:
    - Hybrid retrieval MUST score sparse (BM25) across the *entire* corpus, not only dense hits.
    - We want the index to be reproducible and loadable in the API process.

    Notes:
    - rank-bm25 computes scores in O(N) per query; that is acceptable for small/medium local corpora.
      For large scale, you'd replace this with a real inverted index (Elasticsearch/OpenSearch/Lucene).
    """

    INDEX_VERSION = 2

    def __init__(
        self,
        *,
        chunk_ids: list[str],
        tokenized_docs: list[list[str]],
        tokenizer_config: BM25Config | None = None,
    ) -> None:
        if len(chunk_ids) != len(tokenized_docs):
            raise ValueError("chunk_ids and tokenized_docs must have the same length")
        self.chunk_ids = chunk_ids
        self.tokenized_docs = tokenized_docs
        self.tokenizer_config = tokenizer_config or BM25Config()
        self._normalizer = BM25TextNormalizer(self.tokenizer_config)
        self._bm25 = BM25Okapi(self.tokenized_docs)

    @classmethod
    def build(
        cls,
        texts_by_chunk_id: dict[str, str],
        tokenizer_config: BM25Config | None = None,
    ) -> BM25PersistentIndex:
        # Preserve deterministic order by sorting keys. This makes evaluation reproducible.
        normalizer = BM25TextNormalizer(tokenizer_config)
        chunk_ids = sorted(texts_by_chunk_id.keys())
        tokenized = [normalizer.tokenize(texts_by_chunk_id[cid]) for cid in chunk_ids]
        return cls(
            chunk_ids=chunk_ids,
            tokenized_docs=tokenized,
            tokenizer_config=tokenizer_config,
        )

    def save(self, index_dir: str) -> None:
        out = Path(index_dir)
        out.mkdir(parents=True, exist_ok=True)
        meta = {
            "version": self.INDEX_VERSION,
            "num_docs": len(self.chunk_ids),
            "tokenizer": "configurable",
            "tokenizer_config": self.tokenizer_config.model_dump(),
        }
        (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        with (out / "bm25.pkl").open("wb") as f:
            pickle.dump(
                {
                    "chunk_ids": self.chunk_ids,
                    "tokenized_docs": self.tokenized_docs,
                },
                f,
            )

    @classmethod
    def load(cls, index_dir: str) -> BM25PersistentIndex:
        p = Path(index_dir)
        meta_path = p / "meta.json"
        data_path = p / "bm25.pkl"
        if not meta_path.exists() or not data_path.exists():
            raise FileNotFoundError(
                f"BM25 index missing in {index_dir}. Build it via scripts/build_index.py (or make index)."
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if int(meta.get("version", 0)) != cls.INDEX_VERSION:
            raise ValueError(f"Unsupported BM25 index version: {meta.get('version')}")
        with data_path.open("rb") as f:
            obj = pickle.load(f)
        return cls(
            chunk_ids=list(obj["chunk_ids"]),
            tokenized_docs=list(obj["tokenized_docs"]),
            tokenizer_config=BM25Config.model_validate(meta.get("tokenizer_config", {})),
        )

    def query(
        self,
        q: str,
        top_k: int,
        filter_fn: Callable[[str], bool] | None = None,
    ) -> list[BM25DocHit]:
        """Return top_k matches with optional filtering.

        filter_fn takes chunk_id and returns True if that chunk is eligible.
        We still score the full corpus (requirement), but we drop ineligible items from the ranked list.
        """

        q_tokens = self._normalizer.tokenize(q)
        scores = self._bm25.get_scores(q_tokens)
        ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
        hits: list[BM25DocHit] = []
        for idx, s in ranked:
            cid = self.chunk_ids[idx]
            if filter_fn is not None and not filter_fn(cid):
                continue
            hits.append(BM25DocHit(idx=int(idx), chunk_id=cid, score=float(s)))
            if len(hits) >= top_k:
                break
        return hits
