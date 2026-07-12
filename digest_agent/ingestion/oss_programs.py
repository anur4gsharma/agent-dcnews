from __future__ import annotations

import logging

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)

KNOWN_PROGRAMS = [
    {
        "title": "Google Summer of Code 2026",
        "url": "https://summerofcode.withgoogle.com/",
        "source": "Google",
        "raw_text": "Open-source mentorship program by Google. Stipend provided. Students and beginners welcome.",
        "category": "fellowship",
        "deadline": "Check website for application window",
    },
    {
        "title": "MLH Fellowship",
        "url": "https://fellowship.mlh.io/",
        "source": "MLH",
        "raw_text": "12-week internship alternative. Open source, SWE, and production tracks. Stipend provided.",
        "category": "fellowship",
        "deadline": "Rolling applications",
    },
    {
        "title": "Outreachy Internships",
        "url": "https://www.outreachy.org/",
        "source": "Outreachy",
        "raw_text": "Paid remote internships in open source for underrepresented groups in tech.",
        "category": "fellowship",
        "deadline": "Check website for next round",
    },
    {
        "title": "LFX Mentorship (Linux Foundation)",
        "url": "https://mentorship.lfx.linuxfoundation.org/",
        "source": "Linux Foundation",
        "raw_text": "Mentorship across CNCF, Hyperledger, and LF projects. Stipend provided.",
        "category": "fellowship",
        "deadline": "Rolling — multiple cohorts per year",
    },
    {
        "title": "Season of KDE",
        "url": "https://season.kde.org/",
        "source": "KDE",
        "raw_text": "Contribute to KDE open-source projects with mentorship. Great for beginners.",
        "category": "fellowship",
        "deadline": "Check website for next round",
    },
]


async def fetch_oss_programs(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Return active open-source programs after reachability check."""
    items: list[NormalizedItem] = []
    for program in KNOWN_PROGRAMS:
        try:
            resp = await client.head(program["url"], follow_redirects=True)
            if resp.status_code >= 400:
                continue
        except Exception:
            continue

        item = normalize_item(
            title=program["title"], url=program["url"], source=program["source"],
            timestamp=now_utc(), raw_text=program["raw_text"],
            tier=2, category=program["category"],
            deadline=program.get("deadline", "Unknown"),
        )
        if item:
            items.append(item)

    LOGGER.info("Fetched %s open-source program opportunities", len(items))
    return items
