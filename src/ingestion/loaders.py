from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader


@dataclass(frozen=True)
class Page:
    source: str
    page: int
    text: str


def load_pdf(path: Path) -> list[Page]:
    try:
        reader = PdfReader(str(path))
        pages: list[Page] = []
        for i, p in enumerate(reader.pages):
            txt = p.extract_text() or ""
            pages.append(Page(source=str(path), page=i + 1, text=txt))
        return pages
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF '{path}': {exc}") from exc


def load_txt(path: Path) -> list[Page]:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"Failed to read text file '{path}': {exc}") from exc
    return [Page(source=str(path), page=1, text=txt)]


def load_html(path: Path) -> list[Page]:
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(f"Failed to read HTML file '{path}': {exc}") from exc
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return [Page(source=str(path), page=1, text=text)]


def iter_documents(raw_dir: str, exts: list[str]) -> Iterator[Path]:
    root = Path(raw_dir)
    if not root.exists():
        return
    exts_l = {e.lower() for e in exts}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts_l:
            yield p
