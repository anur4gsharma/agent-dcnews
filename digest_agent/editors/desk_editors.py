from __future__ import annotations

from digest_agent.editors.gemini_client import GeminiEditorClient


TECH_SYSTEM_PROMPT = """You are the Tech News Editor.
Rank Tier 1 wire items by genuine significance for an AI/tech reader.
Downweight press-release rehashes and pure virality.
Upweight primary-source announcements, technical substance, ecosystem impact, and novelty.
Return the top 8 as JSON array objects with title, url, why_it_matters, source, rank."""

OPPORTUNITIES_SYSTEM_PROMPT = """You are the Opportunities Editor.
Rank Tier 2 wire items by fit to the user's interests and skill level, not just recency.
Prefer concrete jobs, competitions, grants, hackathons, and calls for builders.
Return the top 8 as JSON array objects with title, url, why_it_matters, type, rank."""


def run_tech_news_editor(client: GeminiEditorClient, wire_items: list[dict]) -> list[dict]:
    candidates = [item for item in wire_items if int(item.get("tier", 1)) == 1]
    fallback = [
        {
            "title": item["title"],
            "url": item["url"],
            "why_it_matters": item.get("one_line_summary", ""),
            "source": item.get("source", ""),
            "rank": index + 1,
        }
        for index, item in enumerate(sorted(candidates, key=lambda x: x.get("novelty_score", 0), reverse=True)[:8])
    ]
    result = client.generate_json(
        system_prompt=TECH_SYSTEM_PROMPT,
        user_payload={"wire_items": candidates},
        fallback=fallback,
    )
    return _coerce_ranked(result, fallback, item_type="news")


def run_opportunities_editor(client: GeminiEditorClient, wire_items: list[dict], profile: dict) -> list[dict]:
    candidates = [item for item in wire_items if int(item.get("tier", 1)) == 2]
    fallback = [
        {
            "title": item["title"],
            "url": item["url"],
            "why_it_matters": item.get("one_line_summary", ""),
            "type": item.get("category", "opportunity"),
            "rank": index + 1,
        }
        for index, item in enumerate(sorted(candidates, key=lambda x: x.get("novelty_score", 0), reverse=True)[:8])
    ]
    result = client.generate_json(
        system_prompt=OPPORTUNITIES_SYSTEM_PROMPT,
        user_payload={
            "profile": {
                "interests": profile.get("interests", []),
                "skill_level": profile.get("skill_level", "intermediate"),
            },
            "wire_items": candidates,
        },
        fallback=fallback,
    )
    return _coerce_ranked(result, fallback, item_type="opportunity")


def _coerce_ranked(result: object, fallback: list[dict], *, item_type: str) -> list[dict]:
    if not isinstance(result, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(result[:8]):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)] if fallback else {}
        key = "source" if item_type == "news" else "type"
        cleaned.append(
            {
                "title": str(item.get("title") or base.get("title", "")),
                "url": str(item.get("url") or base.get("url", "")),
                "why_it_matters": str(item.get("why_it_matters") or base.get("why_it_matters", "")),
                key: str(item.get(key) or base.get(key, "")),
                "rank": int(item.get("rank") or index + 1),
            }
        )
    return cleaned or fallback

