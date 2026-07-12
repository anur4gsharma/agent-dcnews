from __future__ import annotations

import logging
import re

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)


async def fetch_all_competitions(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Fetch AI/ML competitions from multiple platforms."""
    items: list[NormalizedItem] = []
    fetchers = [
        _fetch_aicrowd(client),
        _fetch_zindi(client),
        _fetch_drivendata(client),
        _fetch_huggingface_competitions(client),
    ]
    import asyncio
    results = await asyncio.gather(*fetchers, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            LOGGER.warning("Competition fetch failed: %s", result)
            continue
        items.extend(result)

    LOGGER.info("Fetched %s total competitions", len(items))
    return items


async def _fetch_aicrowd(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://www.aicrowd.com/challenges",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("AIcrowd scrape skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    for match in re.finditer(
        r'<a[^>]+href="(/challenges/[^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>',
        response.text, flags=re.S,
    ):
        url = f"https://www.aicrowd.com{match.group(1)}"
        title = " ".join(match.group(2).split()).strip()
        if not title:
            continue
        item = normalize_item(
            title=title, url=url, source="AIcrowd", timestamp=now_utc(),
            raw_text=title, tier=2, category="competition",
        )
        if item:
            items.append(item)
    return items[:15]


async def _fetch_zindi(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://zindi.africa/competitions",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("Zindi scrape skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    for match in re.finditer(
        r'<a[^>]+href="(/competitions/[^"]+)"[^>]*>.*?<h[234][^>]*>(.*?)</h[234]>',
        response.text, flags=re.S,
    ):
        url = f"https://zindi.africa{match.group(1)}"
        title = " ".join(match.group(2).split()).strip()
        if not title:
            continue
        item = normalize_item(
            title=title, url=url, source="Zindi", timestamp=now_utc(),
            raw_text=title, tier=2, category="competition",
        )
        if item:
            items.append(item)
    return items[:15]


async def _fetch_drivendata(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://www.drivendata.org/competitions/",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("DrivenData scrape skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    for match in re.finditer(
        r'<a[^>]+href="(/competitions/\d+/[^"]*)"[^>]*>.*?<h[234][^>]*>(.*?)</h[234]>',
        response.text, flags=re.S,
    ):
        url = f"https://www.drivendata.org{match.group(1)}"
        title = " ".join(match.group(2).split()).strip()
        if not title:
            continue
        item = normalize_item(
            title=title, url=url, source="DrivenData", timestamp=now_utc(),
            raw_text=title, tier=2, category="competition",
        )
        if item:
            items.append(item)
    return items[:15]


async def _fetch_huggingface_competitions(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://huggingface.co/competitions",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        if response.status_code != 200:
            return []
    except Exception as exc:
        LOGGER.info("HuggingFace competitions skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    for match in re.finditer(
        r'<a[^>]+href="(/competitions/[^"]+)"[^>]*>(.*?)</a>',
        response.text, flags=re.S,
    ):
        url = f"https://huggingface.co{match.group(1)}"
        title = " ".join(re.sub(r'<[^>]+>', ' ', match.group(2)).split()).strip()
        if not title or len(title) < 5:
            continue
        item = normalize_item(
            title=title, url=url, source="HuggingFace", timestamp=now_utc(),
            raw_text=title, tier=2, category="competition",
        )
        if item:
            items.append(item)
    return items[:15]
