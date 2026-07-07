from __future__ import annotations

from datetime import date

from digest_agent.editors.gemini_client import GeminiEditorClient


CHIEF_SYSTEM_PROMPT = """You are the Chief Editor for a weekly AI/tech digest.
Use Reddit sentiment as a tiebreaker: prefer stories that are actually being discussed, but do not let virality override substance.
Produce final JSON with date, top_news, and top_opportunities.
top_news has exactly up to 5 objects with title, url, why_it_matters, source.
top_opportunities has exactly up to 5 objects with title, url, why_it_matters, type."""


def run_chief_editor(
    client: GeminiEditorClient,
    *,
    tech_candidates: list[dict],
    opportunity_candidates: list[dict],
    sentiment_items: list[dict],
    digest_date: date,
) -> dict:
    fallback = {
        "date": digest_date.isoformat(),
        "top_news": [
            {
                "title": item["title"],
                "url": item["url"],
                "why_it_matters": item["why_it_matters"],
                "source": item.get("source", ""),
            }
            for item in tech_candidates[:5]
        ],
        "top_opportunities": [
            {
                "title": item["title"],
                "url": item["url"],
                "why_it_matters": item["why_it_matters"],
                "type": item.get("type", "opportunity"),
            }
            for item in opportunity_candidates[:5]
        ],
    }
    result = client.generate_json(
        system_prompt=CHIEF_SYSTEM_PROMPT,
        user_payload={
            "date": digest_date.isoformat(),
            "tech_candidates": tech_candidates,
            "opportunity_candidates": opportunity_candidates,
            "sentiment_items": sentiment_items,
        },
        fallback=fallback,
    )
    return _coerce_digest(result, fallback)


def _coerce_digest(result: object, fallback: dict) -> dict:
    if not isinstance(result, dict):
        return fallback
    return {
        "date": str(result.get("date") or fallback["date"]),
        "top_news": _coerce_list(result.get("top_news"), fallback["top_news"], "source"),
        "top_opportunities": _coerce_list(result.get("top_opportunities"), fallback["top_opportunities"], "type"),
    }


def _coerce_list(value: object, fallback: list[dict], extra_key: str) -> list[dict]:
    if not isinstance(value, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(value[:5]):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)] if fallback else {}
        cleaned.append(
            {
                "title": str(item.get("title") or base.get("title", "")),
                "url": str(item.get("url") or base.get("url", "")),
                "why_it_matters": str(item.get("why_it_matters") or base.get("why_it_matters", "")),
                extra_key: str(item.get(extra_key) or base.get(extra_key, "")),
            }
        )
    return cleaned or fallback

