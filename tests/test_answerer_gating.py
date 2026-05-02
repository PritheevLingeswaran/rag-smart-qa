from __future__ import annotations

from dataclasses import dataclass

from generation.answerer import Answerer, _should_disable_remote_generation
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


class _StubClientVerifierMismatch:
    def __init__(self) -> None:
        self.calls = 0

    def chat(self, **_: object) -> tuple[str, _Usage]:
        self.calls += 1
        if self.calls == 1:
            return (
                '{"answer":"Supported text [x:p1:c0].","cited_chunk_ids":["x:p1:c0"],'
                '"refusal":{"is_refusal":false,"reason":""}}',
                _Usage(),
            )
        return (
            '{"verdict":"mismatch","score":0.05,"reason":"Verifier detected unsupported claim."}',
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


def test_external_verifier_mismatch_penalizes_confidence_to_refusal() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    settings.generation.min_confidence_for_answer = 0.35
    answerer = Answerer(settings)
    answerer.client = _StubClientVerifierMismatch()
    answerer._disable_remote_generation = False
    out = answerer.generate("What is supported?", [_hit("x:p1:c0", 0.9, "Supported text")])
    assert out.refusal.is_refusal is True
    assert out.external_verification is not None
    assert out.external_verification.mismatch_detected is True
    assert out.confidence == 0.0


def test_no_hits_exposes_retrieval_failure_classification() -> None:
    settings = Settings()
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate("What is missing?", [])
    assert out.refusal.is_refusal is True
    assert out.retrieval_failure_reason == "no_retrieval"
    assert out.debug is not None
    assert out.debug["final_selection_reasoning"] == "No candidates retrieved."



def test_fallback_extracts_presenter_name_count_from_title_slide() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "how many names are there?",
        [
            _hit(
                "deepfakes_presentation.pdf:p1:c0",
                0.9,
                "THE DEATH OF TRUST\n"
                "By Mathew Anu Joy (RA2411026010225) "
                "Pritheev Lingeswaran (RA2411026010228) "
                "Thamaraiselvan (RA2411026010247)",
            )
        ],
    )
    assert out.refusal.is_refusal is False
    assert "there are 3 names" in out.answer.lower()
    assert "Mathew Anu Joy" in out.answer
    assert "[deepfakes_presentation.pdf:p1:c0]" in out.answer


def test_uncited_llm_answer_recovers_with_grounded_name_count_fallback() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer.client = _StubClientNoCitations()
    answerer._disable_remote_generation = False
    out = answerer.generate(
        "how many names are there?",
        [
            _hit(
                "deepfakes_presentation.pdf:p1:c0",
                0.9,
                "By Mathew Anu Joy (RA2411026010225) "
                "Pritheev Lingeswaran (RA2411026010228) "
                "Thamaraiselvan (RA2411026010247)",
            )
        ],
    )
    assert out.refusal.is_refusal is False
    assert "there are 3 names" in out.answer.lower()


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


def test_remote_generation_stays_disabled_for_offline_test_config() -> None:
    settings = Settings()
    settings.embeddings.openai.api_key = "test"
    settings.embeddings.openai.base_url = "http://localhost:9999/v1"
    assert _should_disable_remote_generation(settings) is True


def test_remote_generation_is_allowed_in_dev_with_real_api_key() -> None:
    settings = Settings()
    settings.app.environment = "dev"
    settings.embeddings.openai.api_key = "sk-real-key"
    settings.embeddings.openai.base_url = None
    assert _should_disable_remote_generation(settings) is False


def test_hard_negative_supervisor_query_refuses_without_evidence() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "Who supervised this project?",
        [
            _hit(
                "project:p1:c0",
                0.9,
                "The project title is Production-Grade Hybrid RAG System. "
                "The authors are Pritheev and Thamaraiselvan.",
            )
        ],
    )
    assert out.refusal.is_refusal is True
    assert out.answer == "I don't know based on the provided documents"


def test_multi_hop_title_and_authors_answer_uses_same_evidence() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "What is the title and who are the authors?",
        [
            _hit(
                "deepfakes:p1:c0",
                0.9,
                "THE DEATH OF TRUST\n"
                "By Mathew Anu Joy (RA2411026010225) "
                "Pritheev Lingeswaran (RA2411026010228)",
            )
        ],
    )
    assert out.refusal.is_refusal is False
    assert "The Death Of Trust" in out.answer
    assert "Mathew Anu Joy" in out.answer
    assert "[deepfakes:p1:c0]" in out.answer


def test_conflicting_supervisor_evidence_fails_safely() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "Who was the supervisor?",
        [
            _hit("project:p1:c0", 0.9, "Supervisor: Alice Kumar"),
            _hit("project:p2:c0", 0.88, "Supervisor: Bob Raman"),
        ],
    )
    assert out.refusal.is_refusal is True
    assert out.answer == "I don't know based on the provided documents"
    assert "conflicting evidence" in out.refusal.reason.lower()


def test_confidence_threshold_blocks_uncertain_answer() -> None:
    settings = Settings()
    settings.retrieval.refuse_if_top_score_below = 0.0
    settings.retrieval.refuse_if_top_gap_below = 0.0
    settings.generation.min_confidence_for_answer = 0.95
    answerer = Answerer(settings)
    answerer._disable_remote_generation = True
    out = answerer.generate(
        "What is the title and who are the authors?",
        [
            _hit(
                "deepfakes:p1:c0",
                0.55,
                "THE DEATH OF TRUST\nBy Mathew Anu Joy (RA2411026010225)",
            )
        ],
    )
    assert out.refusal.is_refusal is True
    assert out.answer == "I don't know based on the provided documents"
    assert "confidence" in out.refusal.reason.lower()
