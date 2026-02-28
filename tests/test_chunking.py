from preprocessing.chunking import chunk_text
from utils.settings import ChunkingConfig


def test_token_chunking_basic():
    cfg = ChunkingConfig(strategy="token", chunk_size=50, chunk_overlap=10)
    text = "Hello world. " * 200
    chunks = chunk_text(text, cfg)
    assert len(chunks) > 2
    assert all(c.text.strip() for c in chunks)


def test_char_chunking_overlap():
    cfg = ChunkingConfig(strategy="char", max_chars_fallback=50, chunk_overlap=10)
    text = "a" * 120
    chunks = chunk_text(text, cfg)
    assert len(chunks) == 3
