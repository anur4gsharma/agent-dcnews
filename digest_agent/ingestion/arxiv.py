from __future__ import annotations

import logging
from datetime import timedelta

import feedparser
import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)
ARXIV_URL = "https://export.arxiv.org/api/query"
CATEGORIES = ("cs.AI", "cs.LG", "cs.CL")


async def fetch_arxiv(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    query = " OR ".join(f"cat:{category}" for category in CATEGORIES)
    response = await client.get(
        ARXIV_URL,
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": "50",
        },
    )
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    cutoff = now_utc() - timedelta(days=lookback_days)

    items: list[NormalizedItem] = []
    for entry in feed.entries:
        item = normalize_item(
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            source="arXiv",
            timestamp=entry.get("published", ""),
            raw_text=entry.get("summary", ""),
            tier=1,
        )
        if item and item.timestamp >= cutoff:
            items.append(item)

    LOGGER.info("Fetched %s arXiv items", len(items))
    return items

