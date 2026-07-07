from __future__ import annotations

from collections import defaultdict

from digest_agent.editors.gemini_client import GeminiEditorClient
from digest_agent.ingestion.normalize import NormalizedItem


WIRE_SYSTEM_PROMPT = """You are a wire editor for an AI/tech digest.
For each source batch, convert raw items into concise structured JSON.
Heavily penalize items that look like rehashed versions of recently sent headlines.
Output an array of objects with title, url, one_line_summary, category, novelty_score.
novelty_score must be an integer from 1 to 10."""


def run_wire_editor(
    client: GeminiEditorClient,
    items: list[NormalizedItem],
    sent_headlines_last_7_days: list[str],
) -> list[dict]:
    grouped: dict[str, list[NormalizedItem]] = defaultdict(list)
    for item in items:
        grouped[item.source].append(item)

    outputs: list[dict] = []
    for source, batch in grouped.items():
        fallback = [_fallback_wire_item(item, sent_headlines_last_7_days) for item in batch]
        result = client.generate_json(
            system_prompt=WIRE_SYSTEM_PROMPT,
            user_payload={
                "source": source,
                "recent_sent_headlines": sent_headlines_last_7_days,
                "items": [item.to_dict() for item in batch],
            },
            fallback=fallback,
        )
        outputs.extend(_coerce_wire_items(result, fallback))
    return outputs


def _fallback_wire_item(item: NormalizedItem, recent: list[str]) -> dict:
    title_lower = item.title.lower()
    novelty = 5 if any(title_lower in headline.lower() or headline.lower() in title_lower for headline in recent) else 8
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "tier": item.tier,
        "one_line_summary": item.raw_text[:240] or item.title,
        "category": "opportunity" if item.tier == 2 else "tech_news",
        "novelty_score": novelty,
    }


def _coerce_wire_items(result: object, fallback: list[dict]) -> list[dict]:
    if not isinstance(result, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(result):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)]
        cleaned.append(
            {
                "title": str(item.get("title") or base["title"]),
                "url": str(item.get("url") or base["url"]),
                "source": str(item.get("source") or base["source"]),
                "tier": int(item.get("tier") or base["tier"]),
                "one_line_summary": str(item.get("one_line_summary") or base["one_line_summary"]),
                "category": str(item.get("category") or base["category"]),
                "novelty_score": max(1, min(10, int(item.get("novelty_score") or base["novelty_score"]))),
            }
        )
    return cleaned or fallback

