from __future__ import annotations

from datetime import date

from digest_agent.editors.gemini_client import GeminiEditorClient


CHIEF_SYSTEM_PROMPT = """You are the Chief Editor for a weekly AI/tech opportunity digest targeting a CS student focused on AI/ML, startups, and entrepreneurship.

Use Reddit sentiment as a tiebreaker: prefer stories that are actually being discussed.
Ensure diversity across categories — do not let one source dominate.

Produce final JSON with: date, top_news, top_opportunities.

top_news: up to 30 objects with title, url, why_it_matters, source.
- Select from DIVERSE sources. Never include more than 4 items from the same source.
- Prefer items with genuine technical substance over press releases.
- why_it_matters must be an ultra-concise, 1-sentence summary of what is happening. Strip out all filler text, marketing fluff, and background info. Be extremely brief.

top_opportunities: up to 30 objects with title, url, organization, category, mode, deadline, cost, difficulty, why_it_matters, priority_score.
category must be one of: internship, hackathon, competition, event, fellowship, open_source, research.
mode must be one of: Remote, Hybrid, In-person, Unknown.
cost must be one of: Free, Paid, Unknown.
difficulty must be one of: Beginner, Intermediate, Advanced, Unknown.
priority_score is 1-10 — use the FULL range:
  9-10: Perfect match — remote, free, AI/ML focused, approaching deadline, prestigious org
  7-8: Strong match — most criteria met
  5-6: Moderate — relevant but missing some criteria
  3-4: Weak — tangentially related
  1-2: Poor fit
Do NOT give all items the same score. Spread scores across the range based on genuine fit.
why_it_matters must be a compelling 1-sentence explanation of value to an AI/ML student, NOT raw prize/theme data.

Prioritize: Remote, Free, AI/ML focused, student-friendly, approaching deadlines.
CRITICAL RESTRICTION: For 'hackathon' and 'competition' categories, ONLY include items that are strictly Remote/Online OR located in India. You MUST discard any in-person hackathons/competitions located outside of India.
Deprioritize: Paid events, non-tech roles, expired, low-quality."""


def _diverse_select(
    items: list[dict], key: str, limit: int,
    max_per_source: int = 3, max_per_category: int | None = None,
) -> list[dict]:
    """Select items ensuring no single source or category dominates."""
    selected: list[dict] = []
    source_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for item in items:
        source = str(item.get(key, "Unknown"))
        category = str(item.get("category", "other"))
        if source_counts.get(source, 0) >= max_per_source:
            continue
        if max_per_category is not None and category_counts.get(category, 0) >= max_per_category:
            continue
        selected.append(item)
        source_counts[source] = source_counts.get(source, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def run_chief_editor(
    client: GeminiEditorClient,
    *,
    tech_candidates: list[dict],
    opportunity_candidates: list[dict],
    sentiment_items: list[dict],
    digest_date: date,
) -> dict:
    # Build DIVERSE fallback — max 4 per source for news, max 3 per org for opportunities
    diverse_news = _diverse_select(tech_candidates, "source", 30, max_per_source=4, max_per_category=None)
    diverse_opps = _diverse_select(opportunity_candidates, "organization", 30, max_per_source=3, max_per_category=7)

    fallback = {
        "date": digest_date.isoformat(),
        "top_news": [
            {
                "title": item["title"],
                "url": item["url"],
                "why_it_matters": item["why_it_matters"],
                "source": item.get("source", ""),
            }
            for item in diverse_news
        ],
        "top_opportunities": [
            {
                "title": item["title"],
                "url": item["url"],
                "organization": item.get("organization", "Unknown"),
                "category": item.get("category", "opportunity"),
                "mode": item.get("mode", "Remote"),
                "deadline": item.get("deadline", "Unknown"),
                "cost": item.get("cost", "Free"),
                "difficulty": item.get("difficulty", "Intermediate"),
                "why_it_matters": item["why_it_matters"],
                "priority_score": item.get("priority_score", 5),
            }
            for item in diverse_opps
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
    digest = _coerce_digest(result, fallback)
    # Attach sentiment to the digest so delivery layers can use it
    digest["sentiment"] = sentiment_items[:10] if sentiment_items else []
    return digest


def _coerce_digest(result: object, fallback: dict) -> dict:
    if not isinstance(result, dict):
        return fallback
    return {
        "date": str(result.get("date") or fallback["date"]),
        "top_news": _coerce_news_list(result.get("top_news"), fallback["top_news"]),
        "top_opportunities": _coerce_opp_list(result.get("top_opportunities"), fallback["top_opportunities"]),
    }


def _coerce_news_list(value: object, fallback: list[dict]) -> list[dict]:
    if not isinstance(value, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(value[:30]):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)] if fallback else {}
        cleaned.append({
            "title": str(item.get("title") or base.get("title", "")),
            "url": str(item.get("url") or base.get("url", "")),
            "why_it_matters": str(item.get("why_it_matters") or base.get("why_it_matters", "")),
            "source": str(item.get("source") or base.get("source", "")),
        })
    return cleaned or fallback


def _coerce_opp_list(value: object, fallback: list[dict]) -> list[dict]:
    if not isinstance(value, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(value[:30]):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)] if fallback else {}
        cleaned.append({
            "title": str(item.get("title") or base.get("title", "")),
            "url": str(item.get("url") or base.get("url", "")),
            "organization": str(item.get("organization") or base.get("organization", "Unknown")),
            "category": str(item.get("category") or base.get("category", "opportunity")),
            "mode": str(item.get("mode") or base.get("mode", "Remote")),
            "deadline": str(item.get("deadline") or base.get("deadline", "Unknown")),
            "cost": str(item.get("cost") or base.get("cost", "Free")),
            "difficulty": str(item.get("difficulty") or base.get("difficulty", "Intermediate")),
            "why_it_matters": str(item.get("why_it_matters") or base.get("why_it_matters", "")),
            "priority_score": max(1, min(10, int(item.get("priority_score") or base.get("priority_score", 5)))),
        })
    return cleaned or fallback
