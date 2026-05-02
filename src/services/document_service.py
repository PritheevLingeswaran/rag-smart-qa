from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi import HTTPException, UploadFile

from embeddings.factory import build_embeddings_backend
from ingestion.ingest import Chunk, ingest_document_paths, write_chunks
from ingestion.loaders import Page, load_html, load_pdf, load_txt
from retrieval.bm25 import BM25PersistentIndex
from retrieval.corpus import load_chunks_jsonl
from retrieval.retriever import Retriever
from retrieval.vector_store import VectorStore, build_vector_store
from services.metadata_service import MetadataService
from services.storage_service import StorageService
from services.summary_service import SummaryService
from utils.config import ensure_dirs
from utils.hash import sha256_file
from utils.logging import get_logger
from utils.settings import Settings

log = get_logger(__name__)


def _load_pages(path: Path) -> list[Page]:
    if path.suffix.lower() == ".pdf":
        return cast(list[Page], load_pdf(path))
    if path.suffix.lower() in {".txt", ".md"}:
        return cast(list[Page], load_txt(path))
    if path.suffix.lower() in {".html", ".htm"}:
        return cast(list[Page], load_html(path))
    raise ValueError(f"Unsupported file type: {path.suffix}")


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        metadata: MetadataService,
        storage: StorageService,
        summary_service: SummaryService,
    ) -> None:
        self.settings = settings
        self.metadata = metadata
        self.storage = storage
        self.summary_service = summary_service
        ensure_dirs(settings)

    def create_upload_records(
        self,
        *,
        files: list[UploadFile],
        owner_id: str,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        uploaded: list[dict[str, Any]] = []
        max_size = int(self.settings.ingestion.max_upload_size_mb) * 1024 * 1024
        allowed = {ext.lower() for ext in self.settings.ingestion.supported_extensions}
        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in allowed:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
            stored_path, size_bytes = self.storage.save_upload(upload, owner_id=owner_id)
            if size_bytes > max_size:
                self.storage.delete_file(str(stored_path))
                raise HTTPException(
                    status_code=400,
                    detail=f"File {upload.filename} exceeds {self.settings.ingestion.max_upload_size_mb}MB",
                )
            document = {
                "owner_id": owner_id,
                "filename": upload.filename or stored_path.name,
                "stored_path": str(stored_path),
                "file_type": suffix.lstrip("."),
                "size_bytes": size_bytes,
                "indexing_status": "queued",
                "summary_status": "queued" if self.settings.summaries.enabled else "disabled",
                "collection_name": collection_name,
                "metadata": {
                    "original_filename": upload.filename or stored_path.name,
                    "content_type": upload.content_type,
                },
            }
            document_id = self.metadata.upsert_document(document)
            stored_document = self.metadata.get_document(document_id, owner_id)
            uploaded.append(
                {
                    "id": document_id,
                    "filename": document["filename"],
                    "stored_path": str(stored_path),
                    "file_type": document["file_type"],
                    "size_bytes": size_bytes,
                    "indexing_status": "queued",
                    "summary_status": document["summary_status"],
                    "upload_time": stored_document["upload_time"] if stored_document else "",
                }
            )
        return uploaded

    def list_documents(
        self,
        owner_id: str,
        *,
        search: str | None,
        sort: str,
        order: str,
    ) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            self.metadata.list_documents(owner_id, search=search, sort=sort, order=order),
        )

    def get_document_detail(self, document_id: str, owner_id: str) -> dict[str, Any]:
        document = self.metadata.get_document(document_id, owner_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        try:
            page_preview = self._read_preview(document["stored_path"])
        except Exception as exc:
            page_preview = []
            if not document.get("error_message"):
                document["error_message"] = str(exc)
        chunks = self._chunks_for_document(document["stored_path"])
        summary = self.metadata.get_summary(document_id)
        return {
            **document,
            "preview": page_preview,
            "chunks": chunks,
            "summary": summary,
        }

    def delete_document(self, document_id: str, owner_id: str) -> dict[str, Any]:
        document = self.metadata.delete_document(document_id, owner_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        self.storage.delete_file(document["stored_path"])
        self.rebuild_indexes(owner_id=owner_id)
        return cast(dict[str, Any], document)

    def reindex_document(self, document_id: str, owner_id: str) -> dict[str, Any]:
        document = self.metadata.get_document(document_id, owner_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        self.metadata.set_document_status(
            document_id,
            owner_id,
            indexing_status="processing",
            summary_status="processing" if self.settings.summaries.enabled else "disabled",
            error_message=None,
        )
        self.rebuild_indexes(owner_id=owner_id)
        return self.get_document_detail(document_id, owner_id)

    def rebuild_indexes(self, *, owner_id: str) -> None:
        documents = self.metadata.list_all_documents()
        log.info(
            "documents.rebuild.started",
            owner_id=owner_id,
            document_count=len(documents),
        )
        existing_paths: list[Path] = []
        active_documents: list[dict[str, Any]] = []
        for document in documents:
            path = Path(document["stored_path"])
            if path.exists():
                active_documents.append(document)
                existing_paths.append(path)
                self.metadata.set_document_status(
                    document["id"],
                    document["owner_id"],
                    indexing_status="processing",
                    error_message=None,
                )
            else:
                self.metadata.set_document_status(
                    document["id"],
                    document["owner_id"],
                    indexing_status="failed",
                    summary_status="failed" if self.settings.summaries.enabled else "disabled",
                    error_message=f"Missing uploaded file at {path}",
                )

        chunks = ingest_document_paths(self.settings, existing_paths)
        document_by_path = {document["stored_path"]: document for document in active_documents}
        for chunk in chunks:
            document = document_by_path.get(chunk.source)
            if document is None:
                continue
            chunk.metadata.update(
                {
                    "document_id": document["id"],
                    "owner_id": document["owner_id"],
                    "filename": document["filename"],
                    "collection_name": document.get("collection_name"),
                }
            )
        log.info(
            "documents.rebuild.ingested",
            owner_id=owner_id,
            active_documents=len(active_documents),
            chunk_count=len(chunks),
            sample_chunk=(chunks[0].text[:180] if chunks else ""),
        )
        write_chunks(self.settings, chunks)
        self._build_indexes_from_chunks()
        chunks_by_source = self._group_chunks_by_source(chunks)

        for document in active_documents:
            path = Path(document["stored_path"])
            try:
                pages = _load_pages(path)
                page_count = len(pages)
                text = "\n".join(page.text for page in pages)
                chunk_count = len(chunks_by_source.get(str(path), []))

                if not text.strip():
                    summary_status = "failed" if self.settings.summaries.enabled else "disabled"
                    if self.settings.summaries.enabled:
                        summary_payload = self.summary_service.generate_summary(
                            document=document,
                            text=text,
                        )
                        self.metadata.upsert_summary(document["id"], summary_payload)
                        summary_status = summary_payload["status"]
                    self.metadata.set_document_status(
                        document["id"],
                        document["owner_id"],
                        indexing_status="failed",
                        pages=page_count,
                        chunks_created=chunk_count,
                        summary_status=summary_status,
                        error_message=(
                            "Document has no extractable text. It may be a scanned or image-only file."
                        ),
                    )
                    continue

                if chunk_count == 0:
                    self.metadata.set_document_status(
                        document["id"],
                        document["owner_id"],
                        indexing_status="failed",
                        pages=page_count,
                        chunks_created=0,
                        summary_status="failed" if self.settings.summaries.enabled else "disabled",
                        error_message=(
                            "Document text was detected, but no searchable chunks were created."
                        ),
                    )
                    continue

                summary_status = "ready"
                if self.settings.summaries.enabled:
                    self.metadata.set_document_status(
                        document["id"],
                        document["owner_id"],
                        indexing_status="processing",
                        pages=page_count,
                        chunks_created=chunk_count,
                        summary_status="processing",
                    )
                    summary_payload = self.summary_service.generate_summary(
                        document=document,
                        text=text,
                    )
                    self.metadata.upsert_summary(document["id"], summary_payload)
                    summary_status = summary_payload["status"]
                self.metadata.set_document_status(
                    document["id"],
                    document["owner_id"],
                    indexing_status="ready",
                    pages=page_count,
                    chunks_created=chunk_count,
                    summary_status=summary_status,
                    error_message=None,
                )
                log.info(
                    "documents.rebuild.document_ready",
                    document_id=document["id"],
                    filename=document["filename"],
                    page_count=page_count,
                    chunk_count=chunk_count,
                )
            except Exception as exc:
                self.metadata.set_document_status(
                    document["id"],
                    document["owner_id"],
                    indexing_status="failed",
                    summary_status="failed" if self.settings.summaries.enabled else "disabled",
                    error_message=str(exc),
                )
                log.warning(
                    "documents.rebuild.document_failed",
                    document_id=document["id"],
                    filename=document["filename"],
                    error=str(exc),
                )
        self._reset_runtime_caches()
        log.info("documents.rebuild.completed", owner_id=owner_id, active_documents=len(active_documents))

    def get_dashboard(self, owner_id: str) -> dict[str, Any]:
        stats = self.metadata.get_stats(owner_id)
        recent_docs = self.metadata.list_documents(owner_id)[:5]
        recent_sessions = self.metadata.list_sessions(owner_id)[:5]
        return {
            "stats": stats,
            "recent_documents": recent_docs,
            "recent_sessions": recent_sessions,
        }

    def get_retriever_for_mode(self, mode: str) -> Retriever:
        if mode in {"dense", "bm25"}:
            settings = self._make_dense_settings()
        elif mode in {"hybrid_weighted", "hybrid_rrf"}:
            settings = self._make_hybrid_settings()
        elif mode == "hybrid_rrf_rerank":
            settings = self._make_hybrid_settings()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode: {mode}")
        return Retriever(settings, build_vector_store(settings))

    def source_filter_for_owner(self, owner_id: str) -> str:
        return str(Path(self.settings.paths.uploads_dir) / owner_id)

    def _read_preview(self, stored_path: str) -> list[dict[str, Any]]:
        pages = _load_pages(Path(stored_path))
        return [
            {
                "page": page.page,
                "text": page.text[:4000],
            }
            for page in pages[:10]
        ]

    def _chunks_for_document(self, stored_path: str) -> list[dict[str, Any]]:
        chunks_path = Path(self.settings.paths.chunks_dir) / "chunks.jsonl"
        if not chunks_path.exists():
            return []
        chunks, _ = load_chunks_jsonl(str(chunks_path))
        return [
            {
                "chunk_id": chunk.chunk_id,
                "page": chunk.page,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
            if chunk.source == stored_path
        ]

    def _build_indexes_from_chunks(self) -> None:
        chunks_path = Path(self.settings.paths.chunks_dir) / "chunks.jsonl"
        chunks, _ = load_chunks_jsonl(str(chunks_path))
        log.info(
            "documents.index_build.started",
            chunk_count=len(chunks),
            sample_chunk_id=(chunks[0].chunk_id if chunks else None),
        )
        bm25_dir = Path(self.settings.paths.indexes_dir) / "bm25"
        texts_by_id = {chunk.chunk_id: chunk.text for chunk in chunks}
        BM25PersistentIndex.build(
            texts_by_id,
            tokenizer_config=self.settings.retrieval.bm25,
        ).save(str(bm25_dir))

        embedder = build_embeddings_backend(self.settings)
        store: VectorStore = build_vector_store(self.settings)
        store.reset()
        batch = int(self.settings.embeddings.batch_size)
        for start in range(0, len(chunks), batch):
            batch_chunks = chunks[start : start + batch]
            embeddings = embedder.embed_texts([chunk.text for chunk in batch_chunks])
            store.add(batch_chunks, embeddings.vectors)
        store.save()
        manifest = {
            "embedding_provider": self.settings.embeddings.provider,
            "embedding_model": self.settings.embeddings.model,
            "sentence_transformers_model": self.settings.embeddings.sentence_transformers.model_name,
            "vector_store_provider": self.settings.vector_store.provider,
            "bm25_index_version": BM25PersistentIndex.INDEX_VERSION,
            "corpus_hash": sha256_file(chunks_path),
            "chunk_count": len(chunks),
        }
        (Path(self.settings.paths.indexes_dir) / "index_manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        log.info(
            "documents.index_build.completed",
            chunk_count=len(chunks),
            batch_size=batch,
            bm25_docs=len(texts_by_id),
        )

    @staticmethod
    def _group_chunks_by_source(chunks: list[Chunk]) -> dict[str, list[Chunk]]:
        grouped: dict[str, list[Chunk]] = {}
        for chunk in chunks:
            grouped.setdefault(chunk.source, []).append(chunk)
        return grouped

    @staticmethod
    def _reset_runtime_caches() -> None:
        from api import deps

        deps.get_store.cache_clear()
        deps.get_retriever.cache_clear()

    def _make_dense_settings(self) -> Settings:
        settings = self.settings.model_copy(deep=True)
        settings.retrieval.query_rewrite.enabled = False
        settings.retrieval.hybrid.enabled = False
        settings.retrieval.rerank.enabled = True
        settings.api.reload = False
        return settings

    def _make_hybrid_settings(self) -> Settings:
        settings = self._make_dense_settings()
        settings.retrieval.query_rewrite.enabled = self.settings.retrieval.query_rewrite.enabled
        settings.retrieval.hybrid.enabled = True
        settings.retrieval.hybrid.fusion_method = "rrf"
        settings.retrieval.rerank.enabled = True
        return settings
