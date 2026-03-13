from __future__ import annotations

from typing import Any

from generation.answerer import Answerer
from services.document_service import DocumentService
from services.metadata_service import MetadataService
from utils.settings import Settings


class ChatService:
    def __init__(
        self,
        settings: Settings,
        metadata: MetadataService,
        document_service: DocumentService,
    ) -> None:
        self.settings = settings
        self.metadata = metadata
        self.document_service = document_service

    def query(
        self,
        *,
        owner_id: str,
        question: str,
        session_id: str | None,
        retrieval_mode: str,
        top_k: int,
    ) -> dict[str, Any]:
        session = self.metadata.get_session(session_id, owner_id) if session_id else None
        if session is None:
            session = self.metadata.create_session(owner_id, title=question[:60] or "New chat")
        self.metadata.add_message(session["id"], role="user", content=question)

        retriever = self.document_service.get_retriever_for_mode(retrieval_mode)
        retrieval_mode_override = "bm25" if retrieval_mode == "bm25" else None
        retrieval_output = retriever.retrieve(
            question=question,
            top_k=top_k,
            rewrite_override=False,
            mode_override=retrieval_mode_override,
        )
        answerer = Answerer(retriever.settings)
        generation = answerer.generate(question, retrieval_output.hits)

        assistant_message = self.metadata.add_message(
            session["id"],
            role="assistant",
            content=generation.answer,
            confidence=generation.confidence,
            refusal=generation.refusal.is_refusal,
            latency_ms=float(generation.llm_tokens_out or 0),
            metadata={
                "retrieval_mode": retrieval_mode,
                "answerability": generation.answerability,
                "citation_coverage": generation.citation_coverage,
                "metrics": {
                    "embedding_tokens": retrieval_output.embedding_tokens,
                    "embedding_cost_usd": retrieval_output.embedding_cost_usd,
                    "llm_tokens_in": generation.llm_tokens_in,
                    "llm_tokens_out": generation.llm_tokens_out,
                    "llm_cost_usd": generation.llm_cost_usd,
                },
            },
        )

        citations = self.metadata.add_citations(
            assistant_message["id"],
            [
                {
                    "document_id": self._document_id_for_source(hit.source, owner_id),
                    "chunk_id": hit.chunk_id,
                    "source": hit.source,
                    "page": hit.page,
                    "excerpt": hit.text[:800],
                    "score": hit.score,
                }
                for hit in generation.sources
            ],
        )

        return {
            "session_id": session["id"],
            "answer": generation.answer,
            "confidence": generation.confidence,
            "refusal": {
                "is_refusal": generation.refusal.is_refusal,
                "reason": generation.refusal.reason,
            },
            "citations": citations,
            "sources": [
                {
                    "chunk_id": source.chunk_id,
                    "source": source.source,
                    "page": source.page,
                    "score": source.score,
                    "text": source.text,
                }
                for source in generation.sources
            ],
            "timing": {
                "embedding_tokens": retrieval_output.embedding_tokens,
                "embedding_cost_usd": retrieval_output.embedding_cost_usd,
                "llm_tokens_in": generation.llm_tokens_in,
                "llm_tokens_out": generation.llm_tokens_out,
                "llm_cost_usd": generation.llm_cost_usd,
            },
        }

    def list_sessions(self, owner_id: str) -> list[dict[str, Any]]:
        return self.metadata.list_sessions(owner_id)

    def get_session(self, session_id: str, owner_id: str) -> dict[str, Any]:
        session = self.metadata.get_session(session_id, owner_id)
        if session is None:
            raise ValueError("Session not found.")
        return session

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        return self.metadata.delete_session(session_id, owner_id)

    def _document_id_for_source(self, source: str, owner_id: str) -> str | None:
        document = self.metadata.get_document_by_path(source)
        if document is None or document["owner_id"] != owner_id:
            return None
        return document["id"]
