from __future__ import annotations

import asyncio
import logging

import httpx

from digest_agent.ingestion.arxiv import fetch_arxiv
from digest_agent.ingestion.hackernews import fetch_hackernews
from digest_agent.ingestion.kaggle import fetch_kaggle_competitions
from digest_agent.ingestion.normalize import NormalizedItem, dedupe_items, now_utc
from digest_agent.ingestion.reddit_sentiment import fetch_reddit_sentiment
from digest_agent.ingestion.remoteok import fetch_remoteok
from digest_agent.ingestion.rss_sources import fetch_news_rss, fetch_opportunity_rss


LOGGER = logging.getLogger(__name__)


def mock_items() -> tuple[list[NormalizedItem], list[dict]]:
    timestamp = now_utc()
    items = [
        NormalizedItem(
            "Open-source agent framework adds durable task orchestration",
            "https://example.com/agent-framework",
            "Sample News",
            timestamp,
            "A popular agentic systems project added durable execution and inspection tools.",
            1,
        ),
        NormalizedItem(
            "New benchmark highlights data contamination risks in LLM evals",
            "https://example.com/eval-risk",
            "Sample News",
            timestamp,
            "Researchers released a benchmark focused on contamination-resistant evaluation.",
            1,
        ),
        NormalizedItem(
            "Remote ML tooling role for open-source vector search project",
            "https://example.com/vector-role",
            "Sample Opportunity",
            timestamp,
            "A remote role focused on Python, retrieval systems, and open-source ML tooling.",
            2,
        ),
        NormalizedItem(
            "Agentic AI hackathon opens registrations",
            "https://example.com/agent-hackathon",
            "Sample Opportunity",
            timestamp,
            "A weekend hackathon focused on useful personal agents and workflow automation.",
            2,
        ),
    ]
    sentiment = [
        {"title": "Agent framework launch discussion", "subreddit": "MachineLearning", "score": 420, "comments": 88},
        {"title": "Concerns about LLM eval leakage", "subreddit": "technology", "score": 310, "comments": 72},
    ]
    return items, sentiment


async def ingest_all(lookback_days: int, *, mock: bool = False) -> tuple[list[NormalizedItem], list[dict]]:
    if mock:
        LOGGER.info("Using mocked sample data")
        return mock_items()

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        tasks = [
            fetch_hackernews(client, lookback_days),
            fetch_arxiv(client, lookback_days),
            fetch_news_rss(client, lookback_days),
            fetch_remoteok(client, lookback_days),
            fetch_opportunity_rss(client, lookback_days),
            fetch_kaggle_competitions(),
            fetch_reddit_sentiment(client, lookback_days),
        ]
        hn, arxiv, rss, remoteok, opp_rss, kaggle, sentiment = await asyncio.gather(*tasks, return_exceptions=True)

    batches = [hn, arxiv, rss, remoteok, opp_rss, kaggle]
    items: list[NormalizedItem] = []
    for batch in batches:
        if isinstance(batch, Exception):
            LOGGER.warning("Ingestion batch failed: %s", batch)
            continue
        items.extend(batch)

    if isinstance(sentiment, Exception):
        LOGGER.warning("Sentiment batch failed: %s", sentiment)
        sentiment_items: list[dict] = []
    else:
        sentiment_items = sentiment

    deduped = dedupe_items(items)
    LOGGER.info("Ingested %s items, deduped to %s", len(items), len(deduped))
    return deduped, sentiment_items

