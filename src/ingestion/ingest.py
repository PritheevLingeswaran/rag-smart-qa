from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from ingestion.loaders import Page, iter_documents, load_html, load_pdf, load_txt
from preprocessing.pipeline import preprocess_pages_to_chunks
from utils.hash import sha256_text
from utils.logging import get_logger
from utils.settings import Settings

log = get_logger(__name__)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    page: int
    text: str
    text_sha256: str
    metadata: dict[str, object]


def _chunk_id(source: str, page: int, idx: int) -> str:
    base = Path(source).name.replace(" ", "_")
    return f"{base}:p{page}:c{idx}"


def _sanitize_metadata_value(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())


def _pages_from_path(path: Path) -> list[Page]:
    if path.suffix.lower() == ".pdf":
        return cast(list[Page], load_pdf(path))
    if path.suffix.lower() in {".txt", ".md"}:
        return cast(list[Page], load_txt(path))
    if path.suffix.lower() in {".html", ".htm"}:
        return cast(list[Page], load_html(path))
    raise ValueError(f"Unsupported file type: {path.suffix}")


def ingest_documents(settings: Settings) -> list[Chunk]:
    docs = list(iter_documents(settings.paths.raw_dir, settings.ingestion.supported_extensions))
    log.info("ingest.scan", raw_dir=settings.paths.raw_dir, num_files=len(docs))

    chunks: list[Chunk] = []
    seen_doc_hashes: set[str] = set()
    for doc in docs:
        try:
            pages = _pages_from_path(doc)
        except Exception as exc:
            log.warning("ingest.skip_document", source=str(doc), error=str(exc))
            continue
        raw_doc_text = "\n".join(page.text for page in pages)
        if len(raw_doc_text) > int(settings.ingestion.max_document_chars):
            raw_doc_text = raw_doc_text[: int(settings.ingestion.max_document_chars)]
        doc_hash = sha256_text(raw_doc_text)
        if settings.ingestion.deduplicate_documents and doc_hash in seen_doc_hashes:
            log.info("ingest.skip_duplicate", source=str(doc), text_sha256=doc_hash)
            continue
        seen_doc_hashes.add(doc_hash)
        page_chunks = preprocess_pages_to_chunks(settings, pages)
        for page_num, idx, text in page_chunks:
            cid = _chunk_id(str(doc), page_num, idx)
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    source=str(doc),
                    page=page_num,
                    text=text,
                    text_sha256=sha256_text(text),
                    metadata={
                        "source_name": _sanitize_metadata_value(doc.name),
                        "source_path": _sanitize_metadata_value(str(doc)),
                        "document_sha256": doc_hash,
                    },
                )
            )

    log.info("ingest.complete", num_chunks=len(chunks))
    return chunks


def write_chunks(settings: Settings, chunks: Iterable[Chunk]) -> Path:
    out_path = Path(settings.paths.chunks_dir) / "chunks.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    log.info("chunks.written", path=str(out_path))
    return out_path
