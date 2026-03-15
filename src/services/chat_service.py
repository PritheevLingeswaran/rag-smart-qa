from __future__ import annotations

import time
from typing import Any, cast

from generation.answerer import Answerer
from monitoring.query_metrics import (
    record_error,
    record_fallback,
    record_grounded,
    record_refusal,
    record_retrieval_scores,
    record_usage_metrics,
)
from services.document_service import DocumentService
from services.metadata_service import MetadataService
from utils.logging import get_logger
from utils.settings import Settings
from utils.timeout import StageTimeoutError, run_with_timeout

log = get_logger(__name__)


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
        total_started = time.perf_counter()
        retrieval_started = time.perf_counter()
        try:
            retrieval_output = run_with_timeout(
                "retrieval",
                float(self.settings.api.retrieval_timeout_s),
                lambda: retriever.retrieve(
                    question=question,
                    top_k=top_k,
                    rewrite_override=False,
                    mode_override=retrieval_mode_override,
                ),
            )
        except StageTimeoutError as exc:
            record_error("chat_retrieval_timeout")
            record_fallback("chat_retrieval_timeout")
            log.warning(
                "chat.query.retrieval_timeout", error=str(exc), retrieval_mode=retrieval_mode
            )
            return self._degraded_response(
                session_id=cast(str, session["id"]),
                answer="I cannot answer right now because retrieval timed out.",
                reason="Retrieval timed out before evidence could be gathered.",
                total_latency_s=time.perf_counter() - total_started,
            )
        except Exception as exc:
            record_error("chat_retrieval")
            record_fallback("chat_retrieval_error")
            log.exception(
                "chat.query.retrieval_failed", error=str(exc), retrieval_mode=retrieval_mode
            )
            return self._degraded_response(
                session_id=cast(str, session["id"]),
                answer="I cannot answer right now because retrieval is temporarily unavailable.",
                reason="Retrieval backend error.",
                total_latency_s=time.perf_counter() - total_started,
            )
        retrieval_latency_s = time.perf_counter() - retrieval_started
        answerer = Answerer(retriever.settings)
        generation_started = time.perf_counter()
        try:
            generation = run_with_timeout(
                "generation",
                float(self.settings.api.generation_timeout_s),
                lambda: answerer.generate(question, retrieval_output.hits),
            )
        except StageTimeoutError as exc:
            record_error("chat_generation_timeout")
            record_fallback("chat_generation_timeout")
            log.warning("chat.query.generation_timeout", error=str(exc))
            return self._degraded_response(
                session_id=cast(str, session["id"]),
                answer="I found relevant evidence, but answer generation timed out.",
                reason="Generation timed out.",
                total_latency_s=time.perf_counter() - total_started,
                retrieval_output=retrieval_output,
            )
        except Exception as exc:
            record_error("chat_generation")
            record_fallback("chat_generation_error")
            log.exception("chat.query.generation_failed", error=str(exc))
            return self._degraded_response(
                session_id=cast(str, session["id"]),
                answer="I found relevant evidence, but answer generation is temporarily unavailable.",
                reason="Generation backend error.",
                total_latency_s=time.perf_counter() - total_started,
                retrieval_output=retrieval_output,
            )
        generation_latency_s = time.perf_counter() - generation_started
        total_latency_s = time.perf_counter() - total_started
        total_cost = (
            float(retrieval_output.embedding_cost_usd + float(generation.llm_cost_usd or 0.0))
            if generation.llm_cost_usd is not None
            else None
        )
        record_usage_metrics(
            latency_s=total_latency_s,
            retrieval_latency_s=retrieval_latency_s,
            generation_latency_s=generation_latency_s,
            embedding_tokens=int(retrieval_output.embedding_tokens),
            llm_in=generation.llm_tokens_in,
            llm_out=generation.llm_tokens_out,
            total_cost=total_cost,
            route="/api/v1/chat/query",
            rerank_latency_s=self._rerank_latency_s(retrieval_output.debug),
        )
        record_retrieval_scores(generation.sources)
        if generation.refusal.is_refusal:
            record_refusal(generation.refusal.reason)
        if not generation.sources and retrieval_output.hits:
            record_fallback("citation_missing_source")
        record_grounded(generation.answer, generation.sources, generation.refusal.is_refusal)

        assistant_message = self.metadata.add_message(
            session["id"],
            role="assistant",
            content=generation.answer,
            confidence=generation.confidence,
            refusal=generation.refusal.is_refusal,
            latency_ms=round(total_latency_s * 1000.0, 2),
            metadata={
                "retrieval_mode": retrieval_mode,
                "answerability": generation.answerability,
                "citation_coverage": generation.citation_coverage,
                "retrieval_latency_ms": round(retrieval_latency_s * 1000.0, 2),
                "generation_latency_ms": round(generation_latency_s * 1000.0, 2),
                "metrics": {
                    "embedding_tokens": retrieval_output.embedding_tokens,
                    "embedding_cost_usd": retrieval_output.embedding_cost_usd,
                    "llm_tokens_in": generation.llm_tokens_in,
                    "llm_tokens_out": generation.llm_tokens_out,
                    "llm_cost_usd": generation.llm_cost_usd,
                },
            },
        )

        citations_payload = [
            {
                "document_id": self._document_id_for_source(hit.source, owner_id),
                "chunk_id": hit.chunk_id,
                "source": hit.source,
                "page": hit.page,
                "excerpt": hit.text[:800],
                "score": hit.score,
            }
            for hit in generation.sources
        ]
        try:
            citations = self.metadata.add_citations(assistant_message["id"], citations_payload)
        except Exception as exc:
            record_error("chat_citations")
            record_fallback("citation_persist_failed")
            log.exception("chat.query.citation_persist_failed", error=str(exc))
            citations = []

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
                "total_latency_ms": round(total_latency_s * 1000.0, 2),
                "retrieval_latency_ms": round(retrieval_latency_s * 1000.0, 2),
                "generation_latency_ms": round(generation_latency_s * 1000.0, 2),
                "rerank_latency_ms": self._rerank_latency_ms(retrieval_output.debug),
                "embedding_tokens": retrieval_output.embedding_tokens,
                "embedding_cost_usd": retrieval_output.embedding_cost_usd,
                "llm_tokens_in": generation.llm_tokens_in,
                "llm_tokens_out": generation.llm_tokens_out,
                "llm_cost_usd": generation.llm_cost_usd,
            },
        }

    def list_sessions(self, owner_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self.metadata.list_sessions(owner_id))

    def get_session(self, session_id: str, owner_id: str) -> dict[str, Any]:
        session = self.metadata.get_session(session_id, owner_id)
        if session is None:
            raise ValueError("Session not found.")
        return cast(dict[str, Any], session)

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        return cast(bool, self.metadata.delete_session(session_id, owner_id))

    def _document_id_for_source(self, source: str, owner_id: str) -> str | None:
        document = self.metadata.get_document_by_path(source)
        if document is None or document["owner_id"] != owner_id:
            return None
        return cast(str, document["id"])

    @staticmethod
    def _rerank_latency_ms(debug: dict[str, Any] | None) -> float | None:
        if not debug:
            return None
        timings = cast(dict[str, Any], debug.get("timings_ms") or {})
        value = timings.get("rerank")
        return float(value) if value is not None else None

    @classmethod
    def _rerank_latency_s(cls, debug: dict[str, Any] | None) -> float | None:
        value = cls._rerank_latency_ms(debug)
        return (value / 1000.0) if value is not None else None

    def _degraded_response(
        self,
        *,
        session_id: str,
        answer: str,
        reason: str,
        total_latency_s: float,
        retrieval_output: Any | None = None,
    ) -> dict[str, Any]:
        self.metadata.add_message(
            session_id,
            role="assistant",
            content=answer,
            confidence=0.0,
            refusal=True,
            latency_ms=round(total_latency_s * 1000.0, 2),
            metadata={"degraded": True, "reason": reason},
        )
        record_refusal(reason)
        if retrieval_output is not None:
            sources = [
                {
                    "chunk_id": source.chunk.chunk_id,
                    "source": source.chunk.source,
                    "page": source.chunk.page,
                    "score": source.score,
                    "text": source.chunk.text,
                }
                for source in retrieval_output.hits
            ]
        else:
            sources = []
        return {
            "session_id": session_id,
            "answer": answer,
            "confidence": 0.0,
            "refusal": {"is_refusal": True, "reason": reason},
            "citations": [],
            "sources": sources,
            "timing": {
                "total_latency_ms": round(total_latency_s * 1000.0, 2),
                "retrieval_latency_ms": None,
                "generation_latency_ms": None,
                "rerank_latency_ms": self._rerank_latency_ms(
                    getattr(retrieval_output, "debug", None)
                ),
                "embedding_tokens": getattr(retrieval_output, "embedding_tokens", None),
                "embedding_cost_usd": getattr(retrieval_output, "embedding_cost_usd", None),
                "llm_tokens_in": None,
                "llm_tokens_out": None,
                "llm_cost_usd": None,
            },
        }
