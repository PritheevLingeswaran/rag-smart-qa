import io
import os

from fastapi.testclient import TestClient

from api import deps
from api.app import create_app

os.environ["RAG_SKIP_STARTUP_VALIDATION"] = "1"


class FakeDocumentService:
    def create_upload_records(self, *, files, owner_id, collection_name=None):
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

    def rebuild_indexes(self, *, owner_id):
        return None

    def list_documents(self, owner_id, *, search, sort, order):
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

    def get_document_detail(self, document_id, owner_id):
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

    def delete_document(self, document_id, owner_id):
        doc = self.list_documents(owner_id, search=None, sort="upload_time", order="desc")[0]
        return doc

    def reindex_document(self, document_id, owner_id):
        return self.get_document_detail(document_id, owner_id)

    def get_dashboard(self, owner_id):
        return {
            "stats": {
                "total_documents": 1,
                "total_chunks": 2,
                "total_sessions": 1,
                "indexing_status": {"ready": 1},
            },
            "recent_documents": self.list_documents(owner_id, search=None, sort="upload_time", order="desc"),
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
    def query(self, *, owner_id, question, session_id, retrieval_mode, top_k):
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

    def list_sessions(self, owner_id):
        return [
            {
                "id": "session-1",
                "owner_id": owner_id,
                "title": "Test Session",
                "created_at": "2026-03-13T00:00:00Z",
                "updated_at": "2026-03-13T00:00:00Z",
            }
        ]

    def get_session(self, session_id, owner_id):
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

    def delete_session(self, session_id, owner_id):
        return True


class FakeMetadataService:
    def get_summary(self, document_id):
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

    def get_citation(self, citation_id, owner_id):
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
        "/api/upload",
        files=[("files", ("guide.txt", io.BytesIO(b"hello world"), "text/plain"))],
    )
    assert upload.status_code == 200
    assert upload.json()["documents"][0]["filename"] == "guide.txt"

    documents = client.get("/api/documents")
    assert documents.status_code == 200
    assert documents.json()["documents"][0]["id"] == "doc-1"

    detail = client.get("/api/documents/doc-1")
    assert detail.status_code == 200
    assert detail.json()["summary"]["status"] == "ready"

    summary = client.get("/api/documents/doc-1/summary")
    assert summary.status_code == 200
    assert summary.json()["summary"] == "Summary text"

    chat = client.post(
        "/api/chat/query",
        json={"question": "What is this?", "retrieval_mode": "hybrid_rrf", "top_k": 5},
    )
    assert chat.status_code == 200
    assert chat.json()["citations"][0]["chunk_id"] == "chunk-1"

    citation = client.get("/api/citations/cit-1")
    assert citation.status_code == 200
    assert citation.json()["excerpt"] == "cited text"


def test_health_and_readiness_aliases() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_document_service] = _fake_document_service
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/healthz").status_code == 200
