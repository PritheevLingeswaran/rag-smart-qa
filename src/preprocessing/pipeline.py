from __future__ import annotations

from ingestion.loaders import Page
from preprocessing.chunking import chunk_text
from preprocessing.cleaning import clean_text
from utils.settings import Settings


def preprocess_pages_to_chunks(settings: Settings, pages: list[Page]) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for page in pages:
        cleaned = clean_text(page.text, settings.preprocessing.cleaning)
        for ch in chunk_text(cleaned, settings.preprocessing.chunking):
            out.append((page.page, ch.idx, ch.text))
    return out
