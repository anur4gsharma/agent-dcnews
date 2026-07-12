from __future__ import annotations

import logging
import re

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)

DEVPOST_HACKATHONS_URL = "https://devpost.com/api/hackathons"


def _extract_theme_names(themes: object) -> list[str]:
    """Extract clean theme name strings from Devpost's theme objects."""
    if not isinstance(themes, list):
        return []
    names: list[str] = []
    for theme in themes[:5]:
        if isinstance(theme, dict):
            name = theme.get("name", "")
            if name:
                names.append(str(name))
        elif isinstance(theme, str):
            names.append(theme)
    return names


def _extract_deadline(dates_str: str) -> str:
    """Extract the end date from a Devpost submission_period_dates string.

    Devpost formats dates like 'Jul 10 - 12, 2026' or 'Jun 22 - Aug 03, 2026'.
    The deadline is the end date.
    """
    if not dates_str:
        return "Unknown"
    # Match patterns like "Jul 10 - 12, 2026" or "Jun 22 - Aug 03, 2026"
    # Full end date: "Aug 03, 2026" or "12, 2026"
    match = re.search(
        r'-\s*([A-Z][a-z]{2}\s+\d{1,2},\s*\d{4})', dates_str
    )
    if match:
        return match.group(1).strip()
    # Short form: "Jul 10 - 12, 2026" → extract "Jul 12, 2026"
    match = re.search(
        r'([A-Z][a-z]{2})\s+\d{1,2}\s*-\s*(\d{1,2}),\s*(\d{4})', dates_str
    )
    if match:
        return f"{match.group(1)} {match.group(2)}, {match.group(3)}"
    return dates_str.strip()


def _build_summary(hack: dict) -> str:
    """Build a clean, human-readable summary sentence for a hackathon."""
    parts: list[str] = []

    prize = hack.get("prize_amount")
    if prize:
        parts.append(f"Prize pool: {prize}")

    themes = _extract_theme_names(hack.get("themes"))
    if themes:
        parts.append(f"Themes: {', '.join(themes)}")

    registrants = hack.get("registrations_count")
    if registrants:
        parts.append(f"{registrants:,} registrants" if isinstance(registrants, int) else f"{registrants} registrants")

    dates = hack.get("submission_period_dates", "")
    if dates:
        parts.append(f"Dates: {dates}")

    return ". ".join(parts) if parts else hack.get("title", "")


async def fetch_devpost_hackathons(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Fetch upcoming and open hackathons from Devpost JSON API."""
    items: list[NormalizedItem] = []
    for status in ("upcoming", "open"):
        try:
            response = await client.get(
                DEVPOST_HACKATHONS_URL,
                params={"status[]": status, "page": "1"},
                headers={"User-Agent": "ai-opportunity-agent/0.2", "Accept": "application/json"},
            )
            if response.status_code != 200:
                LOGGER.info("Devpost %s returned %s; trying HTML fallback", status, response.status_code)
                items.extend(await _devpost_html_fallback(client))
                continue
            data = response.json()
            hackathons = data.get("hackathons", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            for hack in hackathons:
                title = hack.get("title", "")
                url = hack.get("url", "")
                raw_text = _build_summary(hack)
                deadline = _extract_deadline(hack.get("submission_period_dates", ""))
                item = normalize_item(
                    title=title,
                    url=url,
                    source="Devpost",
                    timestamp=hack.get("submission_period_dates", "") or now_utc(),
                    raw_text=raw_text,
                    tier=2,
                    category="hackathon",
                    deadline=deadline,
                )
                if item:
                    items.append(item)
        except Exception as exc:
            LOGGER.warning("Devpost %s fetch failed: %s", status, exc)

    LOGGER.info("Fetched %s Devpost hackathons", len(items))
    return items[:30]


async def _devpost_html_fallback(client: httpx.AsyncClient) -> list[NormalizedItem]:
    """Fallback: scrape the Devpost hackathons listing page."""
    try:
        response = await client.get(
            "https://devpost.com/hackathons",
            headers={"User-Agent": "ai-opportunity-agent/0.2"},
        )
        response.raise_for_status()
    except Exception:
        return []

    items: list[NormalizedItem] = []
    for match in re.finditer(
        r'<a[^>]+href="(https://[^"]*devpost\.com/[^"]*)"[^>]*>.*?class="title"[^>]*>([^<]+)',
        response.text,
        flags=re.S,
    ):
        url, title = match.group(1), match.group(2).strip()
        item = normalize_item(
            title=title, url=url, source="Devpost", timestamp=now_utc(),
            raw_text=title, tier=2, category="hackathon",
        )
        if item:
            items.append(item)
    return items[:20]
