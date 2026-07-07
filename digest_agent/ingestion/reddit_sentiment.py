from __future__ import annotations

import logging

import httpx


LOGGER = logging.getLogger(__name__)
SUBREDDITS = ("MachineLearning", "technology")


async def fetch_reddit_sentiment(client: httpx.AsyncClient, lookback_days: int) -> list[dict]:
    items: list[dict] = []
    period = "week" if lookback_days > 1 else "day"
    for subreddit in SUBREDDITS:
        try:
            response = await client.get(
                f"https://api.reddit.com/r/{subreddit}/top",
                params={"t": period, "limit": "20"},
                headers={"User-Agent": "ai-tech-digest-agent/0.1 by local"},
            )
            if response.status_code == 403:
                LOGGER.info("Reddit public JSON blocked for r/%s; skipping sentiment fallback", subreddit)
                continue
            response.raise_for_status()
            children = response.json().get("data", {}).get("children", [])
            for child in children:
                data = child.get("data", {})
                items.append(
                    {
                        "title": data.get("title", ""),
                        "url": f"https://reddit.com{data.get('permalink', '')}",
                        "subreddit": subreddit,
                        "score": data.get("score", 0),
                        "comments": data.get("num_comments", 0),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Failed Reddit sentiment fetch for r/%s: %s", subreddit, exc)

    LOGGER.info("Fetched %s Reddit sentiment items", len(items))
    return items
