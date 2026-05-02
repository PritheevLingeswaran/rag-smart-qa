from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from generation.prompts import load_prompt
from utils.logging import get_logger
from utils.openai_client import OpenAIClient
from utils.settings import Settings

log = get_logger(__name__)

QueryIntent = Literal["count", "list", "fact", "summary"]


@dataclass(frozen=True)
class QueryPlan:
    intent: QueryIntent
    semantic_query: str
    lexical_query: str
    rewrite_applied: bool
    reasoning_hops: int = 1
    sub_queries: tuple[str, ...] = ()
    required_facts: tuple[str, ...] = ()


def classify_query(question: str) -> QueryIntent:
    q = " ".join(question.lower().split())
    if re.search(r"\b(how many|number of|count|total)\b", q):
        return "count"
    if re.search(r"\b(list|name all|what are the|which are the|enumerate)\b", q):
        return "list"
    if re.search(r"\b(summarize|summary|overview|brief|tl;dr|recap)\b", q):
        return "summary"
    return "fact"


def build_query_plan(
    settings: Settings,
    client: OpenAIClient,
    question: str,
    *,
    rewrite_enabled: bool,
) -> QueryPlan:
    intent = classify_query(question)
    lexical_query = question.strip()
    if not rewrite_enabled:
        reasoning_hops = (
            _clamp_hops(
                _heuristic_hops(question),
                settings.retrieval.multi_hop_planning.max_hops,
            )
            if settings.retrieval.multi_hop_planning.enabled
            else 1
        )
        return QueryPlan(
            intent=intent,
            semantic_query=lexical_query,
            lexical_query=lexical_query,
            rewrite_applied=False,
            reasoning_hops=reasoning_hops,
            sub_queries=(
                _heuristic_sub_queries(question)
                if settings.retrieval.multi_hop_planning.enabled
                else ()
            ),
            required_facts=(
                _heuristic_required_facts(question)
                if settings.retrieval.multi_hop_planning.enabled
                else ()
            ),
        )

    prompt = load_prompt("prompts/query_rewrite.txt")
    messages = [
        {
            "role": "system",
            "content": (
                "Rewrite user questions for semantic vector retrieval. "
                "Return strict JSON only."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "instructions": prompt,
                    "question": question,
                    "intent": intent,
                    "output_schema": {
                        "semantic_query": "short natural-language semantic rewrite",
                        "reasoning_hops": "integer 1-3",
                        "sub_queries": ["focused retrieval question per hop"],
                        "required_facts": ["facts that must be grounded before answering"],
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        text, _ = client.chat(
            model=settings.retrieval.query_rewrite.model,
            messages=messages,
            temperature=0.0,
            max_output_tokens=96,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        log.warning("query_plan.rewrite_failed_fallback", error=str(e))
        reasoning_hops = (
            _clamp_hops(
                _heuristic_hops(question),
                settings.retrieval.multi_hop_planning.max_hops,
            )
            if settings.retrieval.multi_hop_planning.enabled
            else 1
        )
        return QueryPlan(
            intent=intent,
            semantic_query=lexical_query,
            lexical_query=lexical_query,
            rewrite_applied=False,
            reasoning_hops=reasoning_hops,
            sub_queries=(
                _heuristic_sub_queries(question)
                if settings.retrieval.multi_hop_planning.enabled
                else ()
            ),
            required_facts=(
                _heuristic_required_facts(question)
                if settings.retrieval.multi_hop_planning.enabled
                else ()
            ),
        )

    semantic_query = ""
    try:
        obj = json.loads(text)
        semantic_query = str(obj.get("semantic_query", "")).strip().strip('"')
        raw_hops = obj.get("reasoning_hops", _heuristic_hops(question))
        reasoning_hops = _clamp_hops(raw_hops, settings.retrieval.multi_hop_planning.max_hops)
        sub_queries = _clean_string_list(obj.get("sub_queries", []))
        required_facts = _clean_string_list(obj.get("required_facts", []))
    except Exception:
        semantic_query = text.strip().strip('"')
        reasoning_hops = _clamp_hops(
            _heuristic_hops(question),
            settings.retrieval.multi_hop_planning.max_hops,
        )
        sub_queries = _heuristic_sub_queries(question)
        required_facts = _heuristic_required_facts(question)

    if not semantic_query:
        semantic_query = lexical_query
    if not sub_queries:
        sub_queries = _heuristic_sub_queries(question)
    if not required_facts:
        required_facts = _heuristic_required_facts(question)
    if not settings.retrieval.multi_hop_planning.enabled:
        reasoning_hops = 1
        sub_queries = ()
        required_facts = ()
    else:
        reasoning_hops = max(reasoning_hops, min(len(sub_queries), settings.retrieval.multi_hop_planning.max_hops) or 1)
    return QueryPlan(
        intent=intent,
        semantic_query=semantic_query,
        lexical_query=lexical_query,
        rewrite_applied=semantic_query != lexical_query,
        reasoning_hops=reasoning_hops,
        sub_queries=tuple(sub_queries[: max(0, reasoning_hops - 1)]),
        required_facts=tuple(required_facts[:6]),
    )


def _clamp_hops(value: object, max_hops: int) -> int:
    try:
        hops = int(value)
    except Exception:
        hops = 1
    return max(1, min(max(1, int(max_hops)), hops))


def _clean_string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    cleaned: list[str] = []
    for item in value:
        s = re.sub(r"\s+", " ", str(item)).strip()
        if s and s not in cleaned:
            cleaned.append(s)
    return tuple(cleaned)


def _heuristic_hops(question: str) -> int:
    q = question.lower()
    if re.search(r"\b(compare|relationship|correlat|why|how does|trace|combine)\b", q):
        return 3
    if " and " in q or re.search(r"\b(title.*author|author.*title|before.*after)\b", q):
        return 2
    return 1


def _heuristic_sub_queries(question: str) -> tuple[str, ...]:
    q = question.strip()
    parts = [p.strip(" ?.") for p in re.split(r"\s+\band\b\s+|;", q, flags=re.IGNORECASE)]
    if len(parts) > 1:
        return tuple(p for p in parts if p and p.lower() != q.lower())[:2]
    return ()


def _heuristic_required_facts(question: str) -> tuple[str, ...]:
    q = question.lower()
    facts: list[str] = []
    for label, pattern in (
        ("count", r"\b(how many|count|number|total)\b"),
        ("title", r"\b(title|topic)\b"),
        ("authors", r"\b(author|authors|presenter|presenters)\b"),
        ("supervisor", r"\b(supervisor|advisor|mentor)\b"),
    ):
        if re.search(pattern, q):
            facts.append(label)
    return tuple(facts)
