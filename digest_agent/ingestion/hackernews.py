from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from datetime import timedelta

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)
BASE_URL = "https://hacker-news.firebaseio.com/v0"


async def fetch_hackernews(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    cutoff = now_utc() - timedelta(days=lookback_days)
    response = await client.get(f"{BASE_URL}/topstories.json")
    response.raise_for_status()
    story_ids = response.json()[:50]

    async def fetch_story(story_id: int) -> NormalizedItem | None:
        try:
            story_response = await client.get(f"{BASE_URL}/item/{story_id}.json")
            story_response.raise_for_status()
            story = story_response.json() or {}
            timestamp = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc)
            if timestamp < cutoff:
                return None
            return normalize_item(
                title=story.get("title", ""),
                url=story.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                source="Hacker News",
                timestamp=timestamp,
                raw_text=story.get("text") or story.get("title", ""),
                tier=1,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Skipping Hacker News story %s: %s", story_id, exc)
            return None

    items = [item for item in await asyncio.gather(*(fetch_story(story_id) for story_id in story_ids)) if item]
    LOGGER.info("Fetched %s Hacker News items", len(items))
    return items
