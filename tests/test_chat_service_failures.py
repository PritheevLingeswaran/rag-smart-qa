from __future__ import annotations

from typing import Any

from services.chat_service import ChatService
from utils.timeout import StageTimeoutError


class FakeMetadata:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

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
