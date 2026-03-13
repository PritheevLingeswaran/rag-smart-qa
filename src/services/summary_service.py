from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.openai_client import OpenAIClient
from utils.settings import Settings


class SummaryService:
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

    def generate_summary(
        self,
        *,
        document: dict[str, Any],
        text: str,
    ) -> dict[str, Any]:
        excerpt = text[: int(self.settings.summaries.max_context_chars)]
        if not excerpt.strip():
            return {
                "status": "failed",
                "summary": "",
                "key_insights": [],
                "important_points": [],
                "topics": [],
                "keywords": [],
                "title": document["filename"],
                "error_message": "Document has no extractable text.",
                "method": "empty_document",
            }

        model = self.settings.summaries.model or self.settings.generation.model
        if self.settings.summaries.enabled and self.settings.embeddings.openai.api_key:
            try:
                prompt = (
                    "You are summarizing a document for a professional RAG workspace. "
                    "Return strict JSON with keys: title, summary, key_insights, "
                    "important_points, topics, keywords. Use concise factual outputs.\n\n"
                    f"Filename: {document['filename']}\n\n"
                    f"Document excerpt:\n{excerpt}"
                )
                response, _ = self.client.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Respond with valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_output_tokens=700,
                    response_format={"type": "json_object"},
                )
                payload = json.loads(response)
                return {
                    "status": "ready",
                    "title": payload.get("title") or document["filename"],
                    "summary": payload.get("summary", ""),
                    "key_insights": payload.get("key_insights", [])[: self.settings.summaries.max_points],
                    "important_points": payload.get("important_points", [])[
                        : self.settings.summaries.max_points
                    ],
                    "topics": payload.get("topics", []),
                    "keywords": payload.get("keywords", []),
                    "error_message": None,
                    "method": "openai_chat",
                }
            except Exception as exc:
                return {
                    "status": "failed",
                    "title": document["filename"],
                    "summary": "",
                    "key_insights": [],
                    "important_points": [],
                    "topics": [],
                    "keywords": [],
                    "error_message": str(exc),
                    "method": "openai_chat",
                }

        return self._fallback_summary(document=document, text=excerpt)

    def _fallback_summary(self, *, document: dict[str, Any], text: str) -> dict[str, Any]:
        sentences = [
            sentence.strip()
            for sentence in text.replace("\n", " ").split(".")
            if sentence.strip()
        ]
        key_points = sentences[: self.settings.summaries.max_points]
        keywords = self._keywords_from_text(text)
        summary = ". ".join(key_points[:2]).strip()
        if summary and not summary.endswith("."):
            summary += "."
        return {
            "status": "ready",
            "title": Path(document["filename"]).stem.replace("-", " ").title(),
            "summary": summary or text[:280],
            "key_insights": key_points[: self.settings.summaries.max_points],
            "important_points": key_points[: self.settings.summaries.max_points],
            "topics": keywords[:3],
            "keywords": keywords,
            "error_message": None,
            "method": "extractive_fallback",
        }

    @staticmethod
    def _keywords_from_text(text: str) -> list[str]:
        words = [word.lower() for word in text.split()]
        freq: dict[str, int] = {}
        for word in words:
            normalized = "".join(ch for ch in word if ch.isalnum() or ch == "-")
            if len(normalized) < 4:
                continue
            freq[normalized] = freq.get(normalized, 0) + 1
        ordered = sorted(freq.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ordered[:8]]
