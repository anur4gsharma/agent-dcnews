from __future__ import annotations

import logging
from datetime import timedelta

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)
REMOTEOK_URL = "https://remoteok.com/api"
AI_TAGS = {"ai", "ml", "machine-learning", "artificial-intelligence", "llm"}


async def fetch_remoteok(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    response = await client.get(REMOTEOK_URL, headers={"User-Agent": "ai-tech-digest-agent/0.1"})
    response.raise_for_status()
    payload = response.json()
    jobs = payload[1:] if isinstance(payload, list) else []
    cutoff = now_utc() - timedelta(days=lookback_days)

    items: list[NormalizedItem] = []
    for job in jobs:
        tags = {str(tag).lower() for tag in job.get("tags", [])}
        text = " ".join(str(job.get(key, "")) for key in ("position", "description", "company"))
        if not (AI_TAGS & tags or any(tag in text.lower() for tag in AI_TAGS)):
            continue
        item = normalize_item(
            title=f"{job.get('position', 'AI role')} at {job.get('company', 'Unknown company')}",
            url=job.get("url", ""),
            source="RemoteOK",
            timestamp=job.get("date", ""),
            raw_text=text,
            tier=2,
        )
        if item and item.timestamp >= cutoff:
            items.append(item)

    LOGGER.info("Fetched %s RemoteOK AI/ML opportunities", len(items))
    return items

