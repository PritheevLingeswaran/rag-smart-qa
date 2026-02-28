from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass

from generation.prompts import load_prompt
from retrieval.vector_store import SearchHit
from schemas.response import Refusal, SourceChunk
from utils.logging import get_logger
from utils.openai_client import OpenAIClient
from utils.settings import Settings

log = get_logger(__name__)


@dataclass
class GenerationOutput:
    answer: str
    confidence: float
    sources: list[SourceChunk]
    refusal: Refusal
    llm_tokens_in: int
    llm_tokens_out: int
    llm_cost_usd: float


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _estimate_llm_cost(tokens_in: int, tokens_out: int) -> float:
    in_rate = float(os.environ.get("LLM_USD_PER_1K_INPUT", "0") or 0.0)
    out_rate = float(os.environ.get("LLM_USD_PER_1K_OUTPUT", "0") or 0.0)
    return (tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate


def _build_context(hits: list[SearchHit], max_chars: int = 16000) -> str:
    parts: list[str] = []
    used = 0
    for h in hits:
        c = h.chunk
        block = f"[{c.chunk_id}] source={c.source} page={c.page} score={h.score:.3f}\n{c.text.strip()}\n\n"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "".join(parts)


def _citations_ok(answer: str, cited: list[str]) -> bool:
    if not cited:
        return False
    for cid in cited:
        if f"[{cid}]" not in answer:
            return False
    return True


class Answerer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        oai = settings.embeddings.openai
        self.client = OpenAIClient(
            api_key=oai.api_key,
            base_url=oai.base_url,
            organization=oai.organization,
            timeout_s=oai.request_timeout_s,
            max_retries=oai.max_retries,
        )
        self.system = load_prompt("prompts/system_instructions.txt")
        self.template = load_prompt("prompts/answer_with_citations.txt")
        self.refusal_policy = load_prompt("prompts/refusal_policy.txt")

    def generate(self, question: str, hits: list[SearchHit]) -> GenerationOutput:
        if not hits:
            return GenerationOutput(
                answer="I cannot answer from the provided documents because no relevant evidence was retrieved.",
                confidence=0.0,
                sources=[],
                refusal=Refusal(is_refusal=True, reason="No retrieved evidence above threshold."),
                llm_tokens_in=0,
                llm_tokens_out=0,
                llm_cost_usd=0.0,
            )

        context = _build_context(hits)
        retrieved_ids = [h.chunk.chunk_id for h in hits]

        payload = {
            "QUESTION": question,
            "CONTEXT": context,
            "REFUSAL_POLICY": self.refusal_policy,
            "INSTRUCTIONS": self.template,
        }

        messages = [
            {"role": "system", "content": self.system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

        raw, usage = self.client.chat(
            model=self.settings.generation.model,
            messages=messages,
            temperature=self.settings.generation.temperature,
            max_output_tokens=self.settings.generation.max_output_tokens,
            response_format={"type": "json_object"},
        )

        cost = _estimate_llm_cost(usage.input_tokens, usage.output_tokens)

        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except Exception:
                    parsed = None

        sources = [
            SourceChunk(
                chunk_id=h.chunk.chunk_id,
                source=h.chunk.source,
                page=h.chunk.page,
                score=h.score,
                text=h.chunk.text,
            )
            for h in hits
        ]

        if not isinstance(parsed, dict):
            return GenerationOutput(
                answer="I cannot answer because the model returned an invalid JSON response.",
                confidence=0.0,
                sources=sources,
                refusal=Refusal(is_refusal=True, reason="Invalid model output."),
                llm_tokens_in=usage.input_tokens,
                llm_tokens_out=usage.output_tokens,
                llm_cost_usd=cost,
            )

        answer = str(parsed.get("answer", "")).strip()
        cited = parsed.get("cited_chunk_ids", []) or []
        cited = [c for c in cited if c in retrieved_ids]
        refusal_obj = parsed.get("refusal", {}) or {}
        is_refusal = bool(refusal_obj.get("is_refusal", False))
        reason = str(refusal_obj.get("reason", "")).strip()

        if (
            self.settings.generation.strict_refusal
            and (not is_refusal)
            and (not _citations_ok(answer, cited))
        ):
            is_refusal = True
            reason = "Answer did not include valid citations from retrieved evidence."

        if is_refusal:
            return GenerationOutput(
                answer=answer or "I cannot answer from the provided documents.",
                confidence=0.0,
                sources=sources,
                refusal=Refusal(is_refusal=True, reason=reason or "Refused by policy."),
                llm_tokens_in=usage.input_tokens,
                llm_tokens_out=usage.output_tokens,
                llm_cost_usd=cost,
            )

        # Confidence heuristic from retrieval scores.
        max_s = max(h.score for h in hits)
        mean_s = sum(h.score for h in hits) / len(hits)
        conf = _sigmoid(2.0 * max_s + mean_s - 1.0)
        conf = float(max(0.05, min(0.98, conf)))

        return GenerationOutput(
            answer=answer,
            confidence=conf,
            sources=sources,
            refusal=Refusal(is_refusal=False, reason=""),
            llm_tokens_in=usage.input_tokens,
            llm_tokens_out=usage.output_tokens,
            llm_cost_usd=cost,
        )
