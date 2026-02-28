from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from ingestion.loaders import Page, iter_documents, load_pdf, load_txt
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


def _pages_from_path(path: Path) -> list[Page]:
    if path.suffix.lower() == ".pdf":
        return load_pdf(path)
    if path.suffix.lower() == ".txt":
        return load_txt(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def ingest_documents(settings: Settings) -> list[Chunk]:
    docs = list(iter_documents(settings.paths.raw_dir, settings.ingestion.supported_extensions))
    log.info("ingest.scan", raw_dir=settings.paths.raw_dir, num_files=len(docs))

    chunks: list[Chunk] = []
    for doc in docs:
        pages = _pages_from_path(doc)
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
                    metadata={"source_name": doc.name},
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
