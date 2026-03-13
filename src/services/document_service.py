from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from embeddings.factory import build_embeddings_backend
from ingestion.ingest import Chunk, ingest_documents, write_chunks
from ingestion.loaders import Page, load_html, load_pdf, load_txt
from retrieval.bm25 import BM25PersistentIndex
from retrieval.corpus import load_chunks_jsonl
from retrieval.retriever import Retriever
from retrieval.vector_store import VectorStore, build_vector_store
from services.metadata_service import MetadataService
from services.storage_service import StorageService
from services.summary_service import SummaryService
from utils.config import ensure_dirs
from utils.settings import Settings


def _load_pages(path: Path) -> list[Page]:
    if path.suffix.lower() == ".pdf":
        return load_pdf(path)
    if path.suffix.lower() in {".txt", ".md"}:
        return load_txt(path)
    if path.suffix.lower() in {".html", ".htm"}:
        return load_html(path)
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
        return self.metadata.list_documents(owner_id, search=search, sort=sort, order=order)

    def get_document_detail(self, document_id: str, owner_id: str) -> dict[str, Any]:
        document = self.metadata.get_document(document_id, owner_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        page_preview = self._read_preview(document["stored_path"])
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
        return document

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
        documents = self.metadata.list_documents(owner_id)
        for document in documents:
            self.metadata.set_document_status(
                document["id"],
                owner_id,
                indexing_status="processing",
                error_message=None,
            )

        chunks = ingest_documents(self.settings)
        write_chunks(self.settings, chunks)
        self._build_indexes_from_chunks()
        chunks_by_source = self._group_chunks_by_source(chunks)

        for document in documents:
            path = Path(document["stored_path"])
            try:
                pages = _load_pages(path)
                page_count = len(pages)
                text = "\n".join(page.text for page in pages)
                summary_status = "ready"
                if self.settings.summaries.enabled:
                    self.metadata.set_document_status(
                        document["id"],
                        owner_id,
                        indexing_status="processing",
                        pages=page_count,
                        chunks_created=len(chunks_by_source.get(str(path), [])),
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
                    owner_id,
                    indexing_status="ready",
                    pages=page_count,
                    chunks_created=len(chunks_by_source.get(str(path), [])),
                    summary_status=summary_status,
                    error_message=None,
                )
            except Exception as exc:
                self.metadata.set_document_status(
                    document["id"],
                    owner_id,
                    indexing_status="failed",
                    summary_status="failed" if self.settings.summaries.enabled else "disabled",
                    error_message=str(exc),
                )
        self._reset_runtime_caches()

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
        elif mode == "hybrid_weighted":
            settings = self._make_hybrid_settings(fusion_method="weighted")
        elif mode == "hybrid_rrf":
            settings = self._make_hybrid_settings(fusion_method="rrf")
        elif mode == "hybrid_rrf_rerank":
            settings = self._make_hybrid_settings(fusion_method="rrf", rerank_enabled=True)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported retrieval mode: {mode}")
        return Retriever(settings, build_vector_store(settings))

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
        bm25_dir = Path(self.settings.paths.indexes_dir) / "bm25"
        texts_by_id = {chunk.chunk_id: chunk.text for chunk in chunks}
        BM25PersistentIndex.build(
            texts_by_id,
            tokenizer_config=self.settings.retrieval.bm25,
        ).save(str(bm25_dir))

        embedder = build_embeddings_backend(self.settings)
        store: VectorStore = build_vector_store(self.settings)
        batch = int(self.settings.embeddings.batch_size)
        for start in range(0, len(chunks), batch):
            batch_chunks = chunks[start : start + batch]
            embeddings = embedder.embed_texts([chunk.text for chunk in batch_chunks])
            store.add(batch_chunks, embeddings.vectors)
        store.save()

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
        settings.retrieval.rerank.enabled = False
        settings.api.reload = False
        return settings

    def _make_hybrid_settings(
        self,
        *,
        fusion_method: str,
        rerank_enabled: bool | None = None,
    ) -> Settings:
        settings = self._make_dense_settings()
        settings.retrieval.hybrid.enabled = True
        settings.retrieval.hybrid.fusion_method = fusion_method
        if rerank_enabled is not None:
            settings.retrieval.rerank.enabled = rerank_enabled
        return settings
