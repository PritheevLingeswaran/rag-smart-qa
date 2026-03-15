import io
import os
from typing import Any

from fastapi.testclient import TestClient

from api import deps
from api.app import create_app

os.environ["RAG_SKIP_STARTUP_VALIDATION"] = "1"


class FakeDocumentService:
    settings = type(
        "Settings",
        (),
        {"api": type("API", (), {"max_upload_files": 10})()},
    )()

    def create_upload_records(
        self,
        *,
        files: list[Any],
        owner_id: str,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "doc-1",
                "filename": files[0].filename,
                "stored_path": "/tmp/doc-1.txt",
                "file_type": "txt",
                "size_bytes": 12,
                "indexing_status": "queued",
                "summary_status": "queued",
                "upload_time": "2026-03-13T00:00:00Z",
            }
        ]

    def rebuild_indexes(self, *, owner_id: str) -> None:
        return None

    def list_documents(
        self,
        owner_id: str,
        *,
        search: str | None,
        sort: str,
        order: str,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "doc-1",
                "filename": "guide.txt",
                "stored_path": "/tmp/doc-1.txt",
                "file_type": "txt",
                "size_bytes": 12,
                "pages": 1,
                "chunks_created": 2,
                "upload_time": "2026-03-13T00:00:00Z",
                "indexing_status": "ready",
                "summary_status": "ready",
                "collection_name": None,
                "error_message": None,
                "metadata": {},
            }
        ]

    def get_document_detail(self, document_id: str, owner_id: str) -> dict[str, Any]:
        return {
            "id": document_id,
            "filename": "guide.txt",
            "stored_path": "/tmp/doc-1.txt",
            "file_type": "txt",
            "size_bytes": 12,
            "pages": 1,
            "chunks_created": 2,
            "upload_time": "2026-03-13T00:00:00Z",
            "indexing_status": "ready",
            "summary_status": "ready",
            "collection_name": None,
            "error_message": None,
            "metadata": {},
            "preview": [{"page": 1, "text": "Preview text"}],
            "chunks": [{"chunk_id": "chunk-1", "page": 1, "text": "Chunk text", "metadata": {}}],
            "summary": {
                "document_id": document_id,
                "status": "ready",
                "title": "Guide",
                "summary": "Summary text",
                "key_insights": ["Insight"],
                "important_points": ["Point"],
                "topics": [],
                "keywords": [],
                "generated_at": "2026-03-13T00:00:00Z",
            },
        }

    def delete_document(self, document_id: str, owner_id: str) -> dict[str, Any]:
        doc = self.list_documents(owner_id, search=None, sort="upload_time", order="desc")[0]
        return doc

    def reindex_document(self, document_id: str, owner_id: str) -> dict[str, Any]:
        return self.get_document_detail(document_id, owner_id)

    def get_dashboard(self, owner_id: str) -> dict[str, Any]:
        return {
            "stats": {
                "total_documents": 1,
                "total_chunks": 2,
                "total_sessions": 1,
                "indexing_status": {"ready": 1},
            },
            "recent_documents": self.list_documents(
                owner_id, search=None, sort="upload_time", order="desc"
            ),
            "recent_sessions": [
                {
                    "id": "session-1",
                    "owner_id": owner_id,
                    "title": "Test Session",
                    "created_at": "2026-03-13T00:00:00Z",
                    "updated_at": "2026-03-13T00:00:00Z",
                }
            ],
        }


class FakeChatService:
    def query(
        self,
        *,
        owner_id: str,
        question: str,
        session_id: str | None,
        retrieval_mode: str,
        top_k: int,
    ) -> dict[str, Any]:
        return {
            "session_id": "session-1",
            "answer": "Grounded answer",
            "confidence": 0.88,
            "refusal": {"is_refusal": False, "reason": ""},
            "citations": [
                {
                    "id": "cit-1",
                    "document_id": "doc-1",
                    "chunk_id": "chunk-1",
                    "source": "guide.txt",
                    "page": 1,
                    "excerpt": "cited text",
                    "score": 0.9,
                    "created_at": "2026-03-13T00:00:00Z",
                }
            ],
            "sources": [
                {
                    "chunk_id": "chunk-1",
                    "source": "guide.txt",
                    "page": 1,
                    "score": 0.9,
                    "text": "cited text",
                }
            ],
            "timing": {"latency_ms": 12.5},
        }

    def list_sessions(self, owner_id: str) -> list[dict[str, Any]]:
        return [
            {
                "id": "session-1",
                "owner_id": owner_id,
                "title": "Test Session",
                "created_at": "2026-03-13T00:00:00Z",
                "updated_at": "2026-03-13T00:00:00Z",
            }
        ]

    def get_session(self, session_id: str, owner_id: str) -> dict[str, Any]:
        return {
            "id": session_id,
            "owner_id": owner_id,
            "title": "Test Session",
            "created_at": "2026-03-13T00:00:00Z",
            "updated_at": "2026-03-13T00:00:00Z",
            "messages": [
                {
                    "id": "msg-1",
                    "session_id": session_id,
                    "role": "assistant",
                    "content": "Grounded answer",
                    "confidence": 0.88,
                    "refusal": False,
                    "latency_ms": 12.5,
                    "created_at": "2026-03-13T00:00:00Z",
                    "metadata": {},
                }
            ],
        }

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        return True


class FakeMetadataService:
    def get_summary(self, document_id: str) -> dict[str, Any]:
        return {
            "document_id": document_id,
            "status": "ready",
            "title": "Guide",
            "summary": "Summary text",
            "key_insights": ["Insight"],
            "important_points": ["Point"],
            "topics": [],
            "keywords": [],
            "generated_at": "2026-03-13T00:00:00Z",
        }

    def get_citation(self, citation_id: str, owner_id: str) -> dict[str, Any]:
        return {
            "id": citation_id,
            "document_id": "doc-1",
            "chunk_id": "chunk-1",
            "source": "guide.txt",
            "page": 1,
            "excerpt": "cited text",
            "score": 0.9,
            "created_at": "2026-03-13T00:00:00Z",
        }


def _fake_document_service() -> FakeDocumentService:
    return FakeDocumentService()


def _fake_chat_service() -> FakeChatService:
    return FakeChatService()


def _fake_metadata_service() -> FakeMetadataService:
    return FakeMetadataService()


def _fake_current_user_id() -> str:
    return "local-user"


def test_upload_list_detail_summary_and_chat_routes() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = _fake_document_service
    app.dependency_overrides[deps.get_chat_service] = _fake_chat_service
    app.dependency_overrides[deps.get_metadata_service] = _fake_metadata_service
    app.dependency_overrides[deps.get_current_user_id] = _fake_current_user_id

    client = TestClient(app)

    upload = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("guide.txt", io.BytesIO(b"hello world"), "text/plain"))],
    )
    assert upload.status_code == 200
    assert upload.json()["documents"][0]["filename"] == "guide.txt"

    documents = client.get("/api/v1/documents")
    assert documents.status_code == 200
    assert documents.json()["documents"][0]["id"] == "doc-1"

    detail = client.get("/api/v1/documents/doc-1")
    assert detail.status_code == 200
    assert detail.json()["summary"]["status"] == "ready"

    summary = client.get("/api/v1/documents/doc-1/summary")
    assert summary.status_code == 200
    assert summary.json()["summary"] == "Summary text"

    chat = client.post(
        "/api/v1/chat/query",
        json={"question": "What is this?", "retrieval_mode": "hybrid_rrf", "top_k": 5},
    )
    assert chat.status_code == 200
    assert chat.json()["citations"][0]["chunk_id"] == "chunk-1"

    citation = client.get("/api/v1/citations/cit-1")
    assert citation.status_code == 200
    assert citation.json()["excerpt"] == "cited text"
    assert "retrieval_latency_ms" in chat.json()["timing"]


def test_health_and_readiness_aliases(monkeypatch: Any) -> None:
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = _fake_document_service
    monkeypatch.setattr("api.routes.health.validate_runtime_readiness", lambda: None)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/healthz").status_code == 200
    readiness = client.get("/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["checks"]["runtime"] == "ok"


def test_readiness_returns_structured_503_when_runtime_is_not_ready(monkeypatch: Any) -> None:
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = _fake_document_service

    def _raise_not_ready() -> None:
        raise RuntimeError("Missing chunks file")

    monkeypatch.setattr("api.routes.health.validate_runtime_readiness", _raise_not_ready)
    client = TestClient(app)

    readiness = client.get("/readiness")
    assert readiness.status_code == 503
    payload = readiness.json()
    assert payload["error"]["code"] == "runtime_not_ready"
    assert payload["error"]["message"] == "Missing chunks file"


def test_upload_rejects_too_many_files() -> None:
    app = create_app()
    fake_document_service = FakeDocumentService()
    fake_document_service.settings = type(
        "Settings", (), {"api": type("API", (), {"max_upload_files": 1})()}
    )()
    app.dependency_overrides[deps.get_document_service] = lambda: fake_document_service
    app.dependency_overrides[deps.get_current_user_id] = _fake_current_user_id
    client = TestClient(app)

    response = client.post(
        "/api/v1/documents/upload",
        files=[
            ("files", ("guide-1.txt", io.BytesIO(b"hello"), "text/plain")),
            ("files", ("guide-2.txt", io.BytesIO(b"world"), "text/plain")),
        ],
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "too_many_files"


def test_chat_route_rejects_whitespace_question() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_chat_service] = _fake_chat_service
    app.dependency_overrides[deps.get_current_user_id] = _fake_current_user_id
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat/query",
        json={"question": "   ", "retrieval_mode": "hybrid_rrf", "top_k": 5},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
