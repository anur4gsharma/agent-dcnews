from __future__ import annotations

import asyncio
import logging

import httpx

from digest_agent.ingestion.arxiv import fetch_arxiv
from digest_agent.ingestion.competitions import fetch_all_competitions
from digest_agent.ingestion.devpost import fetch_devpost_hackathons
from digest_agent.ingestion.events import fetch_all_events
from digest_agent.ingestion.github_trending import fetch_github_trending
from digest_agent.ingestion.hackernews import fetch_hackernews
from digest_agent.ingestion.kaggle import fetch_kaggle_competitions
from digest_agent.ingestion.mlh import fetch_mlh_hackathons
from digest_agent.ingestion.normalize import NormalizedItem, dedupe_items, now_utc
from digest_agent.ingestion.oss_programs import fetch_oss_programs
from digest_agent.ingestion.reddit_sentiment import fetch_reddit_sentiment
from digest_agent.ingestion.remoteok import fetch_remoteok
from digest_agent.ingestion.rss_sources import fetch_news_rss, fetch_opportunity_rss, fetch_research_rss


LOGGER = logging.getLogger(__name__)


def mock_items() -> tuple[list[NormalizedItem], list[dict]]:
    timestamp = now_utc()
    items = [
        NormalizedItem("Open-source agent framework adds durable task orchestration",
            "https://example.com/agent-framework", "Sample News", timestamp,
            "A popular agentic systems project added durable execution and inspection tools.", 1, "news"),
        NormalizedItem("New benchmark highlights data contamination risks in LLM evals",
            "https://example.com/eval-risk", "Sample News", timestamp,
            "Researchers released a benchmark focused on contamination-resistant evaluation.", 1, "research"),
        NormalizedItem("Remote ML Engineer Intern at Vector Search Startup",
            "https://example.com/vector-role", "Sample Opportunity", timestamp,
            "A remote internship focused on Python, retrieval systems, and open-source ML tooling.", 2, "internship"),
        NormalizedItem("Agentic AI Hackathon — Build Your Personal Agent",
            "https://example.com/agent-hackathon", "Devpost", timestamp,
            "A weekend hackathon focused on useful personal agents and workflow automation. Free entry.", 2, "hackathon",
            deadline="Aug 15, 2026"),
        NormalizedItem("Kaggle: Global AI Safety Challenge",
            "https://example.com/kaggle-safety", "Kaggle", timestamp,
            "Predict harmful content patterns. Prize: $50,000.", 2, "competition",
            deadline="Aug 15, 2026"),
        NormalizedItem("LFX Mentorship: Kubernetes Observability",
            "https://example.com/lfx-k8s", "Linux Foundation", timestamp,
            "3-month mentorship on Kubernetes observability tooling. $6,000 stipend.", 2, "fellowship"),
        NormalizedItem("AI Builders Summit — Online Conference",
            "https://example.com/ai-summit", "Luma", timestamp,
            "Free online conference for AI builders. Speakers from OpenAI, Google, and startups.", 2, "event"),
    ]
    sentiment = [
        {"title": "Agent framework launch discussion", "url": "https://reddit.com/r/MachineLearning/example1", "subreddit": "MachineLearning", "score": 420, "comments": 88},
        {"title": "Concerns about LLM eval leakage", "url": "https://reddit.com/r/technology/example2", "subreddit": "technology", "score": 310, "comments": 72},
    ]
    return items, sentiment


# Named tasks so we can log per-source results
_SOURCE_NAMES = [
    "Hacker News",
    "arXiv",
    "News RSS",
    "Research RSS",
    "GitHub Trending",
    "RemoteOK",
    "Opportunity RSS",
    "Kaggle",
    "Devpost",
    "MLH",
    "Competitions (AIcrowd/Zindi/DrivenData/HF)",
    "Events (Luma/Eventbrite)",
    "OSS Programs",
]


async def ingest_all(lookback_days: int, *, mock: bool = False) -> tuple[list[NormalizedItem], list[dict]]:
    if mock:
        LOGGER.info("Using mocked sample data")
        return mock_items()

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        tasks = [
            # --- News ---
            fetch_hackernews(client, lookback_days),
            fetch_arxiv(client, lookback_days),
            fetch_news_rss(client, lookback_days),
            fetch_research_rss(client, lookback_days),
            fetch_github_trending(client, lookback_days),
            # --- Opportunities ---
            fetch_remoteok(client, lookback_days),
            fetch_opportunity_rss(client, lookback_days),
            fetch_kaggle_competitions(),
            fetch_devpost_hackathons(client, lookback_days),
            fetch_mlh_hackathons(client, lookback_days),
            fetch_all_competitions(client, lookback_days),
            fetch_all_events(client, lookback_days),
            fetch_oss_programs(client, lookback_days),
            # --- Sentiment ---
            fetch_reddit_sentiment(client, lookback_days),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # All except last result are item batches; last is sentiment
    item_results = results[:-1]
    sentiment_result = results[-1]

    items: list[NormalizedItem] = []
    source_stats: list[str] = []
    for index, batch in enumerate(item_results):
        source_name = _SOURCE_NAMES[index] if index < len(_SOURCE_NAMES) else f"Source {index}"
        if isinstance(batch, Exception):
            LOGGER.warning("❌ %s: FAILED — %s", source_name, batch)
            source_stats.append(f"  ❌ {source_name}: FAILED")
            continue
        count = len(batch)
        items.extend(batch)
        status = "✅" if count > 0 else "⚠️"
        LOGGER.info("%s %s: %s items", status, source_name, count)
        source_stats.append(f"  {status} {source_name}: {count} items")

    if isinstance(sentiment_result, Exception):
        LOGGER.warning("❌ Reddit Sentiment: FAILED — %s", sentiment_result)
        sentiment_items: list[dict] = []
    else:
        sentiment_items = sentiment_result
        LOGGER.info("✅ Reddit Sentiment: %s items", len(sentiment_items))

    deduped = dedupe_items(items)
    LOGGER.info(
        "📊 Ingestion summary: %s raw items → %s after dedup\n%s",
        len(items), len(deduped), "\n".join(source_stats),
    )
    return deduped, sentiment_items
