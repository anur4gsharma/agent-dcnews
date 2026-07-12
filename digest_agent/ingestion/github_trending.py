from __future__ import annotations

import logging
import re

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"
LANGUAGES = ("python", "")  # Python-specific + all languages


async def fetch_github_trending(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    """Fetch trending GitHub repositories (focus on AI/ML repos)."""
    items: list[NormalizedItem] = []
    seen_urls: set[str] = set()

    for lang in LANGUAGES:
        try:
            url = f"{GITHUB_TRENDING_URL}/{lang}" if lang else GITHUB_TRENDING_URL
            params = {"since": "weekly"}
            response = await client.get(
                url, params=params,
                headers={"User-Agent": "ai-opportunity-agent/0.2"},
            )
            response.raise_for_status()
        except Exception as exc:
            LOGGER.warning("GitHub trending (%s) fetch failed: %s", lang or "all", exc)
            continue

        for match in re.finditer(
            r'<article[^>]*>.*?<h2[^>]*>\s*<a[^>]+href="(/[^"]+)"[^>]*>(.*?)</a>.*?</article>',
            response.text,
            flags=re.S,
        ):
            repo_path = match.group(1).strip()
            repo_name = " ".join(match.group(2).split()).strip().replace(" / ", "/")
            repo_url = f"https://github.com{repo_path}"
            if repo_url in seen_urls:
                continue
            seen_urls.add(repo_url)

            # Extract description
            desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', match.group(0), re.S)
            description = " ".join(desc_match.group(1).split()).strip() if desc_match else ""

            # Extract stars
            stars_match = re.search(r'(\d[\d,]*)\s*stars?\s*(?:this|today)', match.group(0), re.S | re.I)
            stars_text = f" | ⭐ {stars_match.group(1)} stars this week" if stars_match else ""

            item = normalize_item(
                title=f"Trending: {repo_name}",
                url=repo_url,
                source="GitHub Trending",
                timestamp=now_utc(),
                raw_text=f"{description}{stars_text}" or repo_name,
                tier=1,
                category="open_source",
            )
            if item:
                items.append(item)

    LOGGER.info("Fetched %s GitHub trending repos", len(items))
    return items[:25]
