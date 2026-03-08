from __future__ import annotations

from dataclasses import dataclass

from generation.answerer import Answerer
from retrieval.bm25 import BM25TextNormalizer
from retrieval.vector_store import IndexedChunk, SearchHit
from utils.settings import Settings


def _hit(chunk_id: str, score: float, text: str) -> SearchHit:
    return SearchHit(
        chunk=IndexedChunk(
            chunk_id=chunk_id,
            source="data/raw/documents/Pritheev_Resume.pdf",
            page=1,
            text=text,
            metadata={},
        ),
        score=score,
    )


def test_refusal_gate_triggers_on_low_top_score() -> None:
    settings = Settings()
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate("How many projects are there?", [_hit("a", 0.10, "text")])
    assert out.refusal.is_refusal is True
    assert "reliable final answer" in out.answer.lower()


def test_ambiguous_hits_are_classified_partial_instead_of_hard_refusal() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.05
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "How many projects are there?",
        [
            _hit("a", 0.70, "Project one (rag-smart-qa)"),
            _hit("b", 0.68, "Project two (realtime-ml-drift)"),
        ],
    )
    assert out.refusal.is_refusal is False
    assert out.answerability == "partially_answerable"


def test_fallback_answer_gets_citation_when_strict_refusal_enabled() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "How many projects are there in the resume?",
        [
            _hit(
                "resume:p1:c1",
                0.9,
                "Production-Grade Hybrid RAG System (rag-smart-qa)\n"
                "Production-Grade Real-Time ML Drift Detection System (realtime-ml-drift)\n"
                "Production-Grade ML Decision & Evaluation Platform (ml-failure-analysis-framework)",
            )
        ],
    )
    assert out.refusal.is_refusal is False
    assert "[resume:p1:c1]" in out.answer


@dataclass
class _Usage:
    input_tokens: int = 10
    output_tokens: int = 20


class _StubClientNoCitations:
    def chat(self, **_: object) -> tuple[str, _Usage]:
        return (
            '{"answer":"This is an unsupported uncited answer.","cited_chunk_ids":[],"refusal":{"is_refusal":false,"reason":""}}',
            _Usage(),
        )


def test_uncited_llm_answer_is_refused_under_strict_policy() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer.client = _StubClientNoCitations()
    answerer._disable_remote_generation = False
    out = answerer.generate("What is the answer?", [_hit("x:p1:c0", 0.9, "Supported text")])
    assert out.refusal.is_refusal is True
    assert "citations" in out.refusal.reason.lower()


def test_bm25_normalizer_collapses_pdf_spaced_words() -> None:
    normalizer = BM25TextNormalizer()
    tokens = normalizer.tokenize("F a s t A P I and V e c t o r D B s")
    assert "fastapi" in tokens
    assert "vectordbs" in tokens


def test_answerer_uses_spaced_resume_text_as_answerable_evidence() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "Does the resume mention FastAPI?",
        [
            _hit(
                "resume:p1:c1",
                0.32,
                "S y s t e m s & D a t a : F a s t A P I , P o s t g r e S Q L , "
                "V e c t o r D B s ( F A I S S / C h r o m a )",
            )
        ],
    )
    assert out.answerability == "answerable"
    assert out.refusal.is_refusal is False
    assert out.answer.lower().startswith("yes")


def test_answerer_extracts_education_from_spaced_resume_text() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "What is the candidate's education?",
        [
            _hit(
                "resume:p1:c6",
                0.35,
                "E D U C A T I O N\n"
                "B . T e c h - C o m p u t e r S c i e n c e E n g i n e e r i n g "
                "( A r t i f i c i a l I n t e l l i g e n c e & M a c h i n e L e a r n i n g )\n"
                "S R M I n s t i t u t e o f S c i e n c e a n d T e c h n o l o g y\n"
                "2 0 2 4 - 2 0 2 8 ( E x p e c t e d )",
            )
        ],
    )
    assert out.refusal.is_refusal is False
    assert "computer science engineering" in out.answer.lower()
