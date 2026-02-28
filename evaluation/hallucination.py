from __future__ import annotations

import re

from utils.openai_client import OpenAIClient


def heuristic_grounded(answer: str, sources: list[str]) -> bool:
    answer_clean = re.sub(r"\[[^\]]+\]", "", answer)
    sentences = [s.strip() for s in re.split(r"[\n\.!?]+", answer_clean) if s.strip()]
    if not sentences:
        return False
    corpus = " ".join(sources).lower()
    for s in sentences:
        s2 = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
        toks = [t for t in s2.split() if len(t) >= 4]
        if not toks:
            continue
        overlap = sum(1 for t in toks if t in corpus)
        if overlap / max(1, len(toks)) < 0.25:
            return False
    return True


def llm_judge_grounded(
    client: OpenAIClient,
    model: str,
    question: str,
    answer: str,
    sources: list[str],
) -> bool:
    context = "\n\n".join(sources)[:12000]
    prompt = (
        "Decide whether the ANSWER is fully supported by the CONTEXT. "
        "Return ONLY 'yes' or 'no'.\n\n"
        f"QUESTION: {question}\n"
        f"ANSWER: {answer}\n"
        f"CONTEXT: {context}\n"
    )
    text, _ = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": "You are a strict fact-checker."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_output_tokens=5,
    )
    return text.strip().lower().startswith("yes")
