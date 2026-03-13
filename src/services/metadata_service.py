from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from utils.settings import Settings


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class MetadataService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_path = Path(settings.paths.app_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL UNIQUE,
                    file_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    pages INTEGER NOT NULL DEFAULT 0,
                    chunks_created INTEGER NOT NULL DEFAULT 0,
                    upload_time TEXT NOT NULL,
                    indexing_status TEXT NOT NULL,
                    summary_status TEXT NOT NULL DEFAULT 'idle',
                    collection_name TEXT,
                    error_message TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS summaries (
                    document_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    title TEXT,
                    summary TEXT,
                    key_insights_json TEXT NOT NULL DEFAULT '[]',
                    important_points_json TEXT NOT NULL DEFAULT '[]',
                    topics_json TEXT NOT NULL DEFAULT '[]',
                    keywords_json TEXT NOT NULL DEFAULT '[]',
                    error_message TEXT,
                    method TEXT,
                    generated_at TEXT,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL,
                    refusal INTEGER NOT NULL DEFAULT 0,
                    latency_ms REAL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS citations (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    document_id TEXT,
                    chunk_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page INTEGER NOT NULL DEFAULT 0,
                    excerpt TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_id, upload_time DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(indexing_status);
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner ON chat_sessions(owner_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at ASC);
                CREATE INDEX IF NOT EXISTS idx_citations_message ON citations(message_id);
                """
            )

    def upsert_document(self, payload: dict[str, Any]) -> str:
        document_id = str(payload.get("id") or uuid4())
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, owner_id, filename, stored_path, file_type, size_bytes, pages,
                    chunks_created, upload_time, indexing_status, summary_status,
                    collection_name, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    owner_id=excluded.owner_id,
                    filename=excluded.filename,
                    stored_path=excluded.stored_path,
                    file_type=excluded.file_type,
                    size_bytes=excluded.size_bytes,
                    pages=excluded.pages,
                    chunks_created=excluded.chunks_created,
                    upload_time=excluded.upload_time,
                    indexing_status=excluded.indexing_status,
                    summary_status=excluded.summary_status,
                    collection_name=excluded.collection_name,
                    error_message=excluded.error_message,
                    metadata_json=excluded.metadata_json
                """,
                (
                    document_id,
                    payload["owner_id"],
                    payload["filename"],
                    payload["stored_path"],
                    payload["file_type"],
                    int(payload.get("size_bytes", 0)),
                    int(payload.get("pages", 0)),
                    int(payload.get("chunks_created", 0)),
                    payload.get("upload_time", utc_now()),
                    payload.get("indexing_status", "queued"),
                    payload.get("summary_status", "idle"),
                    payload.get("collection_name"),
                    payload.get("error_message"),
                    json.dumps(payload.get("metadata", {})),
                ),
            )
        return document_id

    def get_document(self, document_id: str, owner_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ? AND owner_id = ?",
                (document_id, owner_id),
            ).fetchone()
        return self._row_to_document(row) if row else None

    def get_document_by_path(self, stored_path: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE stored_path = ?",
                (stored_path,),
            ).fetchone()
        return self._row_to_document(row) if row else None

    def list_documents(
        self,
        owner_id: str,
        *,
        search: str | None = None,
        sort: str = "upload_time",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        allowed_sort = {
            "upload_time": "upload_time",
            "name": "filename",
            "type": "file_type",
            "status": "indexing_status",
        }
        sort_column = allowed_sort.get(sort, "upload_time")
        sort_order = "ASC" if order.lower() == "asc" else "DESC"
        query = "SELECT * FROM documents WHERE owner_id = ?"
        params: list[Any] = [owner_id]
        if search:
            query += " AND (filename LIKE ? OR file_type LIKE ? OR indexing_status LIKE ?)"
            token = f"%{search}%"
            params.extend([token, token, token])
        query += f" ORDER BY {sort_column} {sort_order}"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_document(row) for row in rows]

    def delete_document(self, document_id: str, owner_id: str) -> dict[str, Any] | None:
        document = self.get_document(document_id, owner_id)
        if document is None:
            return None
        with self.connection() as conn:
            conn.execute("DELETE FROM summaries WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE id = ? AND owner_id = ?", (document_id, owner_id))
        return document

    def set_document_status(
        self,
        document_id: str,
        owner_id: str,
        *,
        indexing_status: str,
        pages: int | None = None,
        chunks_created: int | None = None,
        error_message: str | None = None,
        summary_status: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        document = self.get_document(document_id, owner_id)
        if document is None:
            return
        metadata = document["metadata"]
        if extra_metadata:
            metadata.update(extra_metadata)
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE documents
                SET indexing_status = ?, pages = ?, chunks_created = ?, error_message = ?,
                    summary_status = ?, metadata_json = ?
                WHERE id = ? AND owner_id = ?
                """,
                (
                    indexing_status,
                    int(pages if pages is not None else document["pages"]),
                    int(chunks_created if chunks_created is not None else document["chunks_created"]),
                    error_message,
                    summary_status if summary_status is not None else document["summary_status"],
                    json.dumps(metadata),
                    document_id,
                    owner_id,
                ),
            )

    def upsert_summary(self, document_id: str, payload: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO summaries (
                    document_id, status, title, summary, key_insights_json, important_points_json,
                    topics_json, keywords_json, error_message, method, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(document_id) DO UPDATE SET
                    status=excluded.status,
                    title=excluded.title,
                    summary=excluded.summary,
                    key_insights_json=excluded.key_insights_json,
                    important_points_json=excluded.important_points_json,
                    topics_json=excluded.topics_json,
                    keywords_json=excluded.keywords_json,
                    error_message=excluded.error_message,
                    method=excluded.method,
                    generated_at=excluded.generated_at
                """,
                (
                    document_id,
                    payload["status"],
                    payload.get("title"),
                    payload.get("summary"),
                    json.dumps(payload.get("key_insights", [])),
                    json.dumps(payload.get("important_points", [])),
                    json.dumps(payload.get("topics", [])),
                    json.dumps(payload.get("keywords", [])),
                    payload.get("error_message"),
                    payload.get("method"),
                    payload.get("generated_at", utc_now()),
                ),
            )

    def get_summary(self, document_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM summaries WHERE document_id = ?",
                (document_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "document_id": row["document_id"],
            "status": row["status"],
            "title": row["title"],
            "summary": row["summary"],
            "key_insights": json.loads(row["key_insights_json"]),
            "important_points": json.loads(row["important_points_json"]),
            "topics": json.loads(row["topics_json"]),
            "keywords": json.loads(row["keywords_json"]),
            "error_message": row["error_message"],
            "method": row["method"],
            "generated_at": row["generated_at"],
        }

    def create_session(self, owner_id: str, title: str) -> dict[str, Any]:
        session_id = str(uuid4())
        now = utc_now()
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO chat_sessions (id, owner_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, owner_id, title, now, now),
            )
        return {
            "id": session_id,
            "owner_id": owner_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

    def touch_session(self, session_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (utc_now(), session_id),
            )

    def list_sessions(self, owner_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chat_sessions WHERE owner_id = ? ORDER BY updated_at DESC",
                (owner_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str, owner_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            session = conn.execute(
                "SELECT * FROM chat_sessions WHERE id = ? AND owner_id = ?",
                (session_id, owner_id),
            ).fetchone()
            if session is None:
                return None
            messages = conn.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return {
            **dict(session),
            "messages": [self._row_to_message(row) for row in messages],
        }

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        with self.connection() as conn:
            result = conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND owner_id = ?",
                (session_id, owner_id),
            )
        return result.rowcount > 0

    def add_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        confidence: float | None = None,
        refusal: bool = False,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid4())
        now = utc_now()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages
                (id, session_id, role, content, confidence, refusal, latency_ms, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    confidence,
                    1 if refusal else 0,
                    latency_ms,
                    now,
                    json.dumps(metadata or {}),
                ),
            )
        self.touch_session(session_id)
        return {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "confidence": confidence,
            "refusal": refusal,
            "latency_ms": latency_ms,
            "created_at": now,
            "metadata": metadata or {},
        }

    def add_citations(self, message_id: str, citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = utc_now()
        rows: list[dict[str, Any]] = []
        with self.connection() as conn:
            for citation in citations:
                citation_id = str(uuid4())
                conn.execute(
                    """
                    INSERT INTO citations
                    (id, message_id, document_id, chunk_id, source, page, excerpt, score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        citation_id,
                        message_id,
                        citation.get("document_id"),
                        citation["chunk_id"],
                        citation["source"],
                        int(citation.get("page", 0)),
                        citation["excerpt"],
                        float(citation.get("score", 0.0)),
                        now,
                    ),
                )
                rows.append(
                    {
                        "id": citation_id,
                        "message_id": message_id,
                        "document_id": citation.get("document_id"),
                        "chunk_id": citation["chunk_id"],
                        "source": citation["source"],
                        "page": int(citation.get("page", 0)),
                        "excerpt": citation["excerpt"],
                        "score": float(citation.get("score", 0.0)),
                        "created_at": now,
                    }
                )
        return rows

    def get_citation(self, citation_id: str, owner_id: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT c.*, d.owner_id
                FROM citations c
                JOIN chat_messages m ON m.id = c.message_id
                JOIN chat_sessions s ON s.id = m.session_id
                LEFT JOIN documents d ON d.id = c.document_id
                WHERE c.id = ? AND s.owner_id = ?
                """,
                (citation_id, owner_id),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_stats(self, owner_id: str) -> dict[str, Any]:
        with self.connection() as conn:
            doc_row = conn.execute(
                """
                SELECT COUNT(*) AS total_docs,
                       COALESCE(SUM(chunks_created), 0) AS total_chunks
                FROM documents
                WHERE owner_id = ?
                """,
                (owner_id,),
            ).fetchone()
            status_rows = conn.execute(
                """
                SELECT indexing_status, COUNT(*) AS count
                FROM documents
                WHERE owner_id = ?
                GROUP BY indexing_status
                """,
                (owner_id,),
            ).fetchall()
            chat_count = conn.execute(
                "SELECT COUNT(*) AS total_sessions FROM chat_sessions WHERE owner_id = ?",
                (owner_id,),
            ).fetchone()
        return {
            "total_documents": int(doc_row["total_docs"]),
            "total_chunks": int(doc_row["total_chunks"]),
            "total_sessions": int(chat_count["total_sessions"]),
            "indexing_status": {row["indexing_status"]: int(row["count"]) for row in status_rows},
        }

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "owner_id": row["owner_id"],
            "filename": row["filename"],
            "stored_path": row["stored_path"],
            "file_type": row["file_type"],
            "size_bytes": int(row["size_bytes"]),
            "pages": int(row["pages"]),
            "chunks_created": int(row["chunks_created"]),
            "upload_time": row["upload_time"],
            "indexing_status": row["indexing_status"],
            "summary_status": row["summary_status"],
            "collection_name": row["collection_name"],
            "error_message": row["error_message"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "confidence": row["confidence"],
            "refusal": bool(row["refusal"]),
            "latency_ms": row["latency_ms"],
            "created_at": row["created_at"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
        }
