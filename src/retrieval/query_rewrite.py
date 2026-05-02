from __future__ import annotations

from retrieval.query_planning import build_query_plan
from utils.openai_client import OpenAIClient
from utils.settings import Settings


def rewrite_query(settings: Settings, client: OpenAIClient, question: str) -> str:
    plan = build_query_plan(settings, client, question, rewrite_enabled=True)
    return plan.semantic_query
