from __future__ import annotations

import logging
import re
from datetime import timedelta
from html import unescape

import feedparser
import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)

NEWS_FEEDS = {
    # --- Core AI/Tech ---
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
    "MIT Tech Review AI": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    # --- Lab / Research Blogs ---
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Google DeepMind Blog": "https://deepmind.google/blog/rss.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Microsoft Research": "https://www.microsoft.com/en-us/research/feed/",
    "NVIDIA Blog": "https://blogs.nvidia.com/feed/",
    "HuggingFace Blog": "https://huggingface.co/blog/feed.xml",
    # --- Startup / Product ---
    "Product Hunt": "https://www.producthunt.com/feed",
    "Y Combinator Blog": "https://www.ycombinator.com/blog/rss/",
}

OPPORTUNITY_FEEDS = {
    "TechCrunch AI Funding": "https://techcrunch.com/tag/artificial-intelligence/feed/",
}

RESEARCH_FEEDS = {
    "Papers With Code": "https://paperswithcode.com/latest",
}


async def _fetch_feed(
    client: httpx.AsyncClient,
    source: str,
    url: str,
    *,
    tier: int,
    lookback_days: int,
    category: str = "",
) -> list[NormalizedItem]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except Exception as exc:
        LOGGER.warning("Failed RSS feed %s: %s", source, exc)
        return []

    cutoff = now_utc() - timedelta(days=lookback_days)
    items: list[NormalizedItem] = []
    for entry in feed.entries:
        item = normalize_item(
            title=entry.get("title", ""),
            url=entry.get("link", ""),
            source=source,
            timestamp=entry.get("published") or entry.get("updated") or "",
            raw_text=entry.get("summary", ""),
            tier=tier,
            category=category,
        )
        if item and item.timestamp >= cutoff:
            items.append(item)
    return items


async def fetch_news_rss(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    batches = [
        await _fetch_feed(client, source, url, tier=1, lookback_days=lookback_days, category="news")
        for source, url in NEWS_FEEDS.items()
    ]
    batches.append(await _fetch_anthropic_news_page(client, lookback_days))
    items = [item for batch in batches for item in batch]
    LOGGER.info("Fetched %s news RSS items", len(items))
    return items


async def fetch_opportunity_rss(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    batches = [
        await _fetch_feed(client, source, url, tier=2, lookback_days=lookback_days, category="opportunity")
        for source, url in OPPORTUNITY_FEEDS.items()
    ]
    items = [item for batch in batches for item in batch]
    LOGGER.info("Fetched %s opportunity RSS items", len(items))
    return items


async def fetch_research_rss(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    batches = [
        await _fetch_feed(client, source, url, tier=1, lookback_days=lookback_days, category="research")
        for source, url in RESEARCH_FEEDS.items()
    ]
    items = [item for batch in batches for item in batch]
    LOGGER.info("Fetched %s research RSS items", len(items))
    return items


async def _fetch_anthropic_news_page(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    try:
        response = await client.get("https://www.anthropic.com/news", headers={"User-Agent": "ai-tech-digest-agent/0.1"})
        response.raise_for_status()
    except Exception as exc:
        LOGGER.info("Skipping Anthropic news page fallback: %s", exc)
        return []

    cutoff = now_utc() - timedelta(days=lookback_days)
    items: list[NormalizedItem] = []
    seen_urls: set[str] = set()
    for href, body in re.findall(r'<a\s+href="(/news/[^"]+)"[^>]*>(.*?)</a>', response.text, flags=re.S):
        url = f"https://www.anthropic.com{href}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        text = " ".join(unescape(re.sub(r"<[^>]+>", " ", body)).split())
        date_match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b", text)
        timestamp = date_match.group(0) if date_match else ""
        title = _anthropic_title_from_card(text, date_match.group(0) if date_match else "")
        item = normalize_item(
            title=title, url=url, source="Anthropic News",
            timestamp=timestamp, raw_text=text, tier=1, category="news",
        )
        if item and item.timestamp >= cutoff:
            items.append(item)
    LOGGER.info("Fetched %s Anthropic news page items", len(items))
    return items


def _anthropic_title_from_card(text: str, date_text: str) -> str:
    categories = ("Announcements", "Product", "Research", "Policy", "Company", "Case Study", "Engineering")
    title = text
    if date_text:
        title = title.split(date_text, maxsplit=1)[-1].strip()
    for category in categories:
        if title.startswith(category):
            title = title[len(category) :].strip()
    return title[:180] or text[:180]
