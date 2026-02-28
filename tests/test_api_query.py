from fastapi.testclient import TestClient

from api import deps
from api.app import create_app
from schemas.response import Refusal, SourceChunk


class DummyRetriever:
    def retrieve(self, question: str, top_k: int, filter_source_substr=None, rewrite_override=None):
        from retrieval.vector_store import IndexedChunk, SearchHit

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
    def generate(self, question, hits):
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
                "llm_tokens_in": 0,
                "llm_tokens_out": 0,
                "llm_cost_usd": 0.0,
            },
        )


def test_query_endpoint():
    app = create_app()
    app.dependency_overrides[deps.get_retriever] = lambda: DummyRetriever()
    app.dependency_overrides[deps.get_answerer] = lambda: DummyAnswerer()

    client = TestClient(app)
    r = client.post("/query", json={"query": "warranty?", "top_k": 3})
    assert r.status_code == 200
    j = r.json()
    assert j["refusal"]["is_refusal"] is False
    assert j["sources"][0]["chunk_id"] == "x:p1:c0"
