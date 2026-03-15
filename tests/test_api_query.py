import os
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import deps
from api.app import create_app
from retrieval.vector_store import IndexedChunk, SearchHit
from schemas.response import Refusal, SourceChunk
from utils.timeout import StageTimeoutError


class DummyRetriever:
    def retrieve(
        self,
        question: str,
        top_k: int,
        filter_source_substr: str | None = None,
        rewrite_override: bool | None = None,
    ) -> object:
        chunk = IndexedChunk(
            chunk_id="x:p1:c0", source="doc.txt", page=1, text="Warranty is 12 months.", metadata={}
        )
        return type(
            "R",
            (),
            {
                "query_used": question,
                "hits": [SearchHit(chunk=chunk, score=0.9)],
                "embedding_tokens": 0,
                "embedding_cost_usd": 0.0,
            },
        )


class DummyAnswerer:
    def generate(self, question: str, hits: list[SearchHit]) -> object:
        return type(
            "G",
            (),
            {
                "answer": "The warranty period is 12 months. [x:p1:c0]",
                "confidence": 0.9,
                "sources": [
                    SourceChunk(
                        chunk_id="x:p1:c0",
                        source="doc.txt",
                        page=1,
                        score=0.9,
                        text="Warranty is 12 months.",
                    )
                ],
                "refusal": Refusal(is_refusal=False, reason=""),
                "llm_tokens_in": None,
                "llm_tokens_out": None,
                "llm_cost_usd": None,
                "answerability": "answerable",
                "citation_coverage": 1.0,
            },
        )


class FailingAnswerer:
    def generate(self, question: str, hits: list[SearchHit]) -> None:
        raise RuntimeError("upstream generation error")


def _dummy_retriever() -> DummyRetriever:
    return DummyRetriever()


def _dummy_answerer() -> DummyAnswerer:
    return DummyAnswerer()


def _failing_answerer() -> FailingAnswerer:
    return FailingAnswerer()


def test_query_endpoint() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = _dummy_retriever
    app.dependency_overrides[deps.get_answerer] = _dummy_answerer

    client = TestClient(app)
    r = client.post("/api/v1/query", json={"query": "warranty?", "top_k": 3})
    assert r.status_code == 200
    assert "x-request-id" in r.headers
    j = r.json()
    assert j["refusal"]["is_refusal"] is False
    assert j["sources"][0]["chunk_id"] == "x:p1:c0"
    assert "retrieval_latency_ms" in j["metrics"]
    assert "generation_latency_ms" in j["metrics"]


def test_query_endpoint_generation_failure_returns_refusal() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = _dummy_retriever
    app.dependency_overrides[deps.get_answerer] = _failing_answerer

    client = TestClient(app)
    r = client.post("/api/v1/query", json={"query": "warranty?", "top_k": 3})
    assert r.status_code == 200
    j = r.json()
    assert j["refusal"]["is_refusal"] is True
    assert j["metrics"]["error"] == "generation_failed"
    assert len(j["sources"]) == 1


def test_metrics_endpoint_exposes_grounding_and_refusal_metrics() -> None:
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = _dummy_retriever
    app.dependency_overrides[deps.get_answerer] = _dummy_answerer
    client = TestClient(app)

    _ = client.post("/api/v1/query", json={"query": "warranty?", "top_k": 3})
    mr = client.get("/api/v1/metrics")
    assert mr.status_code == 200
    body = mr.text
    assert "rag_refusals_total" in body
    assert "rag_grounded_answers_total" in body
    assert "rag_retrieval_top_score" in body
    assert "rag_http_requests_total" in body
    assert "rag_http_request_latency_seconds" in body
    assert "rag_generation_latency_seconds" in body


def test_validation_errors_use_structured_error_response() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"query": "", "top_k": 0})
    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["request_id"]
    assert payload["error"]["details"]["errors"]


def test_validation_rejects_whitespace_only_query() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/v1/query", json={"query": "   ", "top_k": 2})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_query_endpoint_retrieval_timeout_returns_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = _dummy_retriever
    app.dependency_overrides[deps.get_answerer] = _dummy_answerer
    monkeypatch.setattr(
        "api.routes.legacy.run_with_timeout",
        lambda stage, timeout_s, fn: (_ for _ in ()).throw(StageTimeoutError(stage, timeout_s)),
    )

    client = TestClient(app)
    response = client.post("/api/v1/query", json={"query": "warranty?", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["refusal"]["is_refusal"] is True
    assert payload["metrics"]["error"] == "retrieval_timeout"


def test_query_endpoint_generation_timeout_returns_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = _dummy_retriever
    app.dependency_overrides[deps.get_answerer] = _dummy_answerer

    def _timeout_generation(
        stage: str,
        timeout_s: float,
        fn: Callable[[], Any],
    ) -> Any:
        if stage == "generation":
            raise StageTimeoutError(stage, timeout_s)
        return fn()

    monkeypatch.setattr("api.routes.legacy.run_with_timeout", _timeout_generation)

    client = TestClient(app)
    response = client.post("/api/v1/query", json={"query": "warranty?", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["refusal"]["is_refusal"] is True
    assert payload["metrics"]["error"] == "generation_timeout"


os.environ["RAG_SKIP_STARTUP_VALIDATION"] = "1"
