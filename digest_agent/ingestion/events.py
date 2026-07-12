from __future__ import annotations

import json
import logging
import re

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)


async def fetch_all_events(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Fetch tech events from Luma, Eventbrite, and GDG."""
    import asyncio
    results = await asyncio.gather(
        _fetch_luma(client),
        _fetch_eventbrite_tech(client),
        return_exceptions=True,
    )
    items: list[NormalizedItem] = []
    for result in results:
        if isinstance(result, Exception):
            LOGGER.warning("Event fetch failed: %s", result)
            continue
        items.extend(result)
    LOGGER.info("Fetched %s total events", len(items))
    return items


async def _fetch_luma(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://lu.ma/discover",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("Luma scrape skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    # Try JSON-LD
    for ld_match in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', response.text, re.S):
        try:
            data = json.loads(ld_match.group(1))
            events = data if isinstance(data, list) else [data]
            for event in events:
                if event.get("@type") != "Event":
                    continue
                title = event.get("name", "")
                url = event.get("url", "")
                location = event.get("location", {})
                loc_name = location.get("name", "Online") if isinstance(location, dict) else "Online"
                item = normalize_item(
                    title=title, url=url, source="Luma",
                    timestamp=event.get("startDate", ""),
                    raw_text=f"{title} | {loc_name}", tier=2, category="event",
                )
                if item:
                    items.append(item)
        except (json.JSONDecodeError, TypeError):
            continue

    # Fallback: regex scrape for event cards
    if not items:
        for match in re.finditer(
            r'<a[^>]+href="(https://lu\.ma/[^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>',
            response.text, flags=re.S,
        ):
            url = match.group(1)
            title = " ".join(re.sub(r'<[^>]+>', ' ', match.group(2)).split()).strip()
            if not title:
                continue
            item = normalize_item(
                title=title, url=url, source="Luma", timestamp=now_utc(),
                raw_text=title, tier=2, category="event",
            )
            if item:
                items.append(item)

    return items[:20]


async def _fetch_eventbrite_tech(client: httpx.AsyncClient) -> list[NormalizedItem]:
    try:
        response = await client.get(
            "https://www.eventbrite.com/d/online/ai-machine-learning/",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("Eventbrite scrape skipped: %s", exc)
        return []

    items: list[NormalizedItem] = []
    # Try JSON-LD
    for ld_match in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', response.text, re.S):
        try:
            data = json.loads(ld_match.group(1))
            events = data if isinstance(data, list) else [data]
            for event in events:
                if event.get("@type") != "Event":
                    continue
                title = event.get("name", "")
                url = event.get("url", "")
                item = normalize_item(
                    title=title, url=url, source="Eventbrite",
                    timestamp=event.get("startDate", ""),
                    raw_text=title, tier=2, category="event",
                )
                if item:
                    items.append(item)
        except (json.JSONDecodeError, TypeError):
            continue

    # Fallback: regex
    if not items:
        for match in re.finditer(
            r'<a[^>]+href="(https://www\.eventbrite\.com/e/[^"]+)"[^>]*>.*?<h[23][^>]*>(.*?)</h[23]>',
            response.text, flags=re.S,
        ):
            url = match.group(1)
            title = " ".join(re.sub(r'<[^>]+>', ' ', match.group(2)).split()).strip()
            if not title or len(title) < 5:
                continue
            item = normalize_item(
                title=title, url=url, source="Eventbrite", timestamp=now_utc(),
                raw_text=title, tier=2, category="event",
            )
            if item:
                items.append(item)

    return items[:20]
