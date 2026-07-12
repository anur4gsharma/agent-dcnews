from __future__ import annotations

import json
import logging
import re

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)

MLH_EVENTS_URL = "https://mlh.io/seasons/2026/events"


async def fetch_mlh_hackathons(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Fetch upcoming MLH hackathons by scraping the events page."""
    try:
        response = await client.get(
            MLH_EVENTS_URL,
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.warning("MLH events fetch failed: %s", exc)
        return []

    items: list[NormalizedItem] = []
    # Try JSON-LD first
    for ld_match in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', response.text, re.S):
        try:
            data = json.loads(ld_match.group(1))
            events = data if isinstance(data, list) else [data]
            for event in events:
                if event.get("@type") not in ("Event", "Hackathon"):
                    continue
                item = normalize_item(
                    title=event.get("name", ""),
                    url=event.get("url", ""),
                    source="MLH",
                    timestamp=event.get("startDate", ""),
                    raw_text=f"{event.get('name', '')} | {event.get('location', {}).get('name', 'Online')}",
                    tier=2,
                    category="hackathon",
                )
                if item:
                    items.append(item)
        except (json.JSONDecodeError, TypeError):
            continue

    # Fallback: regex scrape
    if not items:
        for match in re.finditer(
            r'class="event-wrapper".*?href="([^"]+)".*?class="event-name"[^>]*>([^<]+).*?class="event-date"[^>]*>([^<]+)',
            response.text,
            flags=re.S,
        ):
            url, title, date_text = match.group(1), match.group(2).strip(), match.group(3).strip()
            if not url.startswith("http"):
                url = f"https://mlh.io{url}"
            item = normalize_item(
                title=title, url=url, source="MLH",
                timestamp=date_text or now_utc(),
                raw_text=f"{title} | {date_text}", tier=2, category="hackathon",
            )
            if item:
                items.append(item)

    LOGGER.info("Fetched %s MLH hackathons", len(items))
    return items[:20]
