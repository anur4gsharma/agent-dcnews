from __future__ import annotations

from digest_agent.editors.gemini_client import GeminiEditorClient
from digest_agent.ingestion.normalize import NormalizedItem


WIRE_SYSTEM_PROMPT = """You are a wire editor for an AI/tech opportunity digest targeting a CS student focused on AI/ML, software engineering, startups, and entrepreneurship.

Convert raw items into concise structured JSON.
Heavily penalize items that look like rehashed versions of recently sent headlines.
Heavily penalize non-AI/ML job listings (e.g. generic admin, HR, non-tech roles).
Boost items that are: remote, free, student-friendly, AI/ML focused, hackathons, competitions, or fellowships.

Output an array of objects with: title, url, source, tier, one_line_summary, category, novelty_score, deadline.
category must be one of: news, research, internship, hackathon, competition, event, fellowship, open_source, opportunity.
novelty_score must be an integer from 1 to 10.
deadline should be a date string or "Unknown"."""


# Maximum items to send to Gemini in a single batch (keeps token count manageable)
_MAX_BATCH_SIZE = 80


def run_wire_editor(
    client: GeminiEditorClient,
    items: list[NormalizedItem],
    sent_headlines_last_7_days: list[str],
) -> list[dict]:
    # Build ALL fallbacks first
    all_fallback = [_fallback_wire_item(item, sent_headlines_last_7_days) for item in items]

    # Send to Gemini as a SINGLE batch (not per-source) to save API calls
    # Limit to top items by tier priority
    sorted_items = sorted(items, key=lambda x: (x.tier, -len(x.raw_text)))
    batch = sorted_items[:_MAX_BATCH_SIZE]
    batch_fallback = [_fallback_wire_item(item, sent_headlines_last_7_days) for item in batch]

    result = client.generate_json(
        system_prompt=WIRE_SYSTEM_PROMPT,
        user_payload={
            "recent_sent_headlines": sent_headlines_last_7_days,
            "items": [item.to_dict() for item in batch],
        },
        fallback=batch_fallback,
    )
    wire_items = _coerce_wire_items(result, batch_fallback)

    # If there are overflow items beyond the batch, add them as fallback
    if len(items) > _MAX_BATCH_SIZE:
        overflow_items = sorted_items[_MAX_BATCH_SIZE:]
        overflow_fallback = [_fallback_wire_item(item, sent_headlines_last_7_days) for item in overflow_items]
        wire_items.extend(overflow_fallback)

    return wire_items


def _fallback_wire_item(item: NormalizedItem, recent: list[str]) -> dict:
    title_lower = item.title.lower()
    novelty = 5 if any(title_lower in headline.lower() or headline.lower() in title_lower for headline in recent) else 8
    category = item.category or ("opportunity" if item.tier == 2 else "news")
    return {
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "tier": item.tier,
        "one_line_summary": item.raw_text[:240] or item.title,
        "category": category,
        "novelty_score": novelty,
        "deadline": item.deadline,
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
                "deadline": str(item.get("deadline") or base.get("deadline", "Unknown")),
            }
        )
    return cleaned or fallback
