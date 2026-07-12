from __future__ import annotations

from digest_agent.editors.gemini_client import GeminiEditorClient


TECH_SYSTEM_PROMPT = """You are the Tech News Editor for a weekly AI/tech digest targeting a CS student focused on AI/ML.
Rank Tier 1 wire items by genuine significance.
Downweight press-release rehashes, pure virality, and non-AI content.
Upweight: primary-source announcements, technical substance, open-source launches, research breakthroughs, ecosystem impact.
Ensure diversity: pick from at least 4 different sources. Max 2 items from any single source.
Return the top 20 as JSON array objects with title, url, why_it_matters, source, rank."""

OPPORTUNITIES_SYSTEM_PROMPT = """You are the Opportunities Editor for a digest targeting a CS student focused on AI/ML, startups, and entrepreneurship.
Rank Tier 2 wire items by fit to the user's profile.

Prioritize:
- Remote opportunities
- Free or stipend-providing programs
- Student-friendly / beginner-intermediate level
- AI/ML, software engineering, startup related
- Hackathons, competitions, fellowships, internships
- Approaching deadlines (sooner = higher priority)

Deprioritize:
- Paid registration events
- Non-tech generic roles (admin, HR, etc.)
- Low-credibility listings
- Opportunities with no clear relevance to AI/ML

For each opportunity, extract these fields from the raw text when possible:
- title, url, organization, category (internship/hackathon/competition/event/fellowship/open_source)
- mode (Remote/Hybrid/In-person), deadline, cost (Free/Paid), difficulty (Beginner/Intermediate/Advanced)
- why_it_matters: Write ONE compelling sentence explaining why this specific opportunity matters for an AI/ML student. Do NOT dump raw metadata.
- priority_score (1-10): Differentiate scores meaningfully:
  - 9-10: Perfect fit — remote, free, AI/ML focused, approaching deadline, prestigious
  - 7-8: Strong fit — most criteria met, minor gaps
  - 5-6: Moderate fit — relevant but not ideal (e.g. paid, or tangentially related)
  - 3-4: Weak fit — barely relevant or missing key criteria
  - 1-2: Poor fit — should probably be excluded

Ensure diversity: pick from at least 4 different sources/organizations. Max 2 items from any single source.
Return the top 20 as a JSON array with those fields. Use "Unknown" for fields you cannot determine."""


# Category priority for fallback ranking (higher = better fit for digest)
_CATEGORY_PRIORITY = {
    "hackathon": 10, "fellowship": 9, "competition": 8, "internship": 7,
    "open_source": 6, "research": 5, "event": 4, "opportunity": 3, "news": 2,
}


def _diverse_select(
    items: list[dict], key: str, limit: int,
    max_per_source: int = 2, max_per_category: int | None = None,
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


def run_tech_news_editor(client: GeminiEditorClient, wire_items: list[dict]) -> list[dict]:
    candidates = [item for item in wire_items if int(item.get("tier", 1)) == 1]
    # Sort by novelty_score descending for fallback
    sorted_candidates = sorted(candidates, key=lambda x: x.get("novelty_score", 0), reverse=True)
    # Enforce source diversity in fallback
    diverse = _diverse_select(sorted_candidates, "source", 20, max_per_source=3, max_per_category=None)
    fallback = [
        {
            "title": item["title"],
            "url": item["url"],
            "why_it_matters": item.get("one_line_summary", ""),
            "source": item.get("source", ""),
            "rank": index + 1,
        }
        for index, item in enumerate(diverse)
    ]
    result = client.generate_json(
        system_prompt=TECH_SYSTEM_PROMPT,
        user_payload={"wire_items": candidates},
        fallback=fallback,
    )
    return _coerce_ranked(result, fallback, item_type="news")


def run_opportunities_editor(client: GeminiEditorClient, wire_items: list[dict], profile: dict) -> list[dict]:
    candidates = [item for item in wire_items if int(item.get("tier", 1)) == 2]
    # Sort by category priority (hackathons/fellowships first) then novelty
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (_CATEGORY_PRIORITY.get(x.get("category", ""), 2), x.get("novelty_score", 0)),
        reverse=True,
    )
    # Enforce source + category diversity in fallback
    diverse = _diverse_select(sorted_candidates, "source", 20, max_per_source=3, max_per_category=4)
    fallback = [
        {
            "title": item["title"],
            "url": item["url"],
            "organization": item.get("source", "Unknown"),
            "category": item.get("category", "opportunity"),
            "mode": "Remote",
            "deadline": item.get("deadline", "Unknown"),
            "cost": "Free",
            "difficulty": "Intermediate",
            "why_it_matters": item.get("one_line_summary", ""),
            "priority_score": item.get("novelty_score", 5),
            "rank": index + 1,
        }
        for index, item in enumerate(diverse)
    ]
    result = client.generate_json(
        system_prompt=OPPORTUNITIES_SYSTEM_PROMPT,
        user_payload={
            "profile": {
                "interests": profile.get("interests", []),
                "skill_level": profile.get("skill_level", "intermediate"),
                "focus_areas": profile.get("focus_areas", []),
            },
            "wire_items": candidates,
        },
        fallback=fallback,
    )
    return _coerce_opportunity_items(result, fallback)


def _coerce_ranked(result: object, fallback: list[dict], *, item_type: str) -> list[dict]:
    if not isinstance(result, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(result[:20]):
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


def _coerce_opportunity_items(result: object, fallback: list[dict]) -> list[dict]:
    if not isinstance(result, list):
        return fallback
    cleaned: list[dict] = []
    for index, item in enumerate(result[:20]):
        if not isinstance(item, dict):
            continue
        base = fallback[min(index, len(fallback) - 1)] if fallback else {}
        cleaned.append(
            {
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
                "rank": int(item.get("rank") or index + 1),
            }
        )
    return cleaned or fallback
