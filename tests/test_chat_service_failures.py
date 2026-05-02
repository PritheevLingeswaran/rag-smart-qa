from __future__ import annotations

from typing import Any

from services.chat_service import ChatService
from utils.timeout import StageTimeoutError


class FakeMetadata:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.documents: list[dict[str, Any]] = []
        self.summary: dict[str, Any] | None = None

    def get_session(self, session_id: str | None, owner_id: str) -> dict[str, Any] | None:
        return None

    def create_session(self, owner_id: str, title: str) -> dict[str, Any]:
        return {"id": "session-1", "owner_id": owner_id, "title": title}

    def add_message(
        self, session_id: str, role: str, content: str, **kwargs: Any
    ) -> dict[str, Any]:
        message = {
            "id": f"msg-{len(self.messages) + 1}",
            "session_id": session_id,
            "role": role,
            "content": content,
            **kwargs,
        }
        self.messages.append(message)
        return message

    def add_citations(
        self, message_id: str, citations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return citations

    def get_document_by_path(self, source: str) -> dict[str, Any] | None:
        return {"id": "doc-1", "owner_id": "local-user"}

    def list_documents(self, owner_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        return self.documents

    def get_summary(self, document_id: str) -> dict[str, Any] | None:
        return self.summary

    def list_sessions(self, owner_id: str) -> list[dict[str, Any]]:
        return []

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        return True


class FakeDocumentService:
    def __init__(self, retriever: Any) -> None:
        self._retriever = retriever

    def get_retriever_for_mode(self, mode: str) -> Any:
        return self._retriever


class FakeRetriever:
    settings: Any

    def __init__(self, settings: Any) -> None:
        self.settings = settings

    def retrieve(self, **kwargs: Any) -> Any:
        raise RuntimeError("boom")


class DummySettings:
    class API:
        retrieval_timeout_s = 0.1
        generation_timeout_s = 0.1

    api = API()


def test_chat_service_returns_degraded_response_on_retrieval_timeout(monkeypatch: Any) -> None:
    metadata = FakeMetadata()
    retriever = FakeRetriever(DummySettings())
    service = ChatService(DummySettings(), metadata, FakeDocumentService(retriever))
    monkeypatch.setattr(
        "services.chat_service.run_with_timeout",
        lambda stage, timeout_s, fn: (_ for _ in ()).throw(StageTimeoutError(stage, timeout_s)),
    )

    payload = service.query(
        owner_id="local-user",
        question="What happened?",
        session_id=None,
        retrieval_mode="hybrid_rrf",
        top_k=5,
    )

    assert payload["refusal"]["is_refusal"] is True
    assert "timed out" in payload["refusal"]["reason"].lower()
    assert payload["citations"] == []


def test_chat_service_returns_degraded_response_on_retrieval_failure(monkeypatch: Any) -> None:
    metadata = FakeMetadata()
    retriever = FakeRetriever(DummySettings())
    service = ChatService(DummySettings(), metadata, FakeDocumentService(retriever))
    monkeypatch.setattr("services.chat_service.run_with_timeout", lambda stage, timeout_s, fn: fn())

    payload = service.query(
        owner_id="local-user",
        question="What happened?",
        session_id=None,
        retrieval_mode="hybrid_rrf",
        top_k=5,
    )

    assert payload["refusal"]["is_refusal"] is True
    assert payload["sources"] == []
    assert "temporarily unavailable" in payload["answer"].lower()


def test_chat_service_answers_document_page_count_without_retrieval(monkeypatch: Any) -> None:
    metadata = FakeMetadata()
    metadata.documents = [
        {
            "id": "doc-1",
            "filename": "UNIT V - DAA.pdf",
            "pages": 28,
            "indexing_status": "ready",
        }
    ]
    retriever = FakeRetriever(DummySettings())
    service = ChatService(DummySettings(), metadata, FakeDocumentService(retriever))

    payload = service.query(
        owner_id="local-user",
        question="how many pages are there in this pdf",
        session_id=None,
        retrieval_mode="hybrid_rrf",
        top_k=5,
    )

    assert payload["answer"] == "The PDF has 28 pages."
    assert payload["confidence"] == 1.0
    assert payload["sources"] == []


def test_chat_service_explains_unit_from_document_summary(monkeypatch: Any) -> None:
    metadata = FakeMetadata()
    metadata.documents = [
        {
            "id": "doc-1",
            "filename": "44884f12-bd93-429a-aac1-49bb744015c7-UNIT V - DAA.pdf",
            "pages": 28,
            "indexing_status": "ready",
        }
    ]
    metadata.summary = {
        "title": "UNIT V - DAA",
        "summary": "This unit covers randomized algorithms, NP-completeness, and string matching.",
        "important_points": ["P and NP classes", "Rabin-Karp pattern matching"],
        "topics": ["randomized algorithms", "NP-completeness", "Rabin-Karp"],
    }
    retriever = FakeRetriever(DummySettings())
    service = ChatService(DummySettings(), metadata, FakeDocumentService(retriever))

    payload = service.query(
        owner_id="local-user",
        question="explain me this unit 5",
        session_id=None,
        retrieval_mode="hybrid_rrf",
        top_k=5,
    )

    assert "Unit V" in payload["answer"]
    assert "28 pages" in payload["answer"]
    assert "NP-completeness" in payload["answer"]
    assert payload["sources"] == []
