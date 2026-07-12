from __future__ import annotations

import logging
import re
from datetime import timedelta

import httpx

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)
REMOTEOK_URL = "https://remoteok.com/api"

# Tags and keywords that indicate AI/ML/SWE/startup relevance
AI_TAGS = {"ai", "ml", "machine-learning", "artificial-intelligence", "llm", "deep-learning", "data-science",
           "nlp", "computer-vision", "neural", "transformer", "generative-ai", "chatgpt", "openai"}
SWE_TAGS = {"python", "software-engineer", "backend", "full-stack", "developer", "engineer", "swe",
            "golang", "rust", "typescript", "react", "node", "devops", "cloud", "kubernetes"}
STARTUP_TAGS = {"startup", "founder", "product", "growth"}
ALL_RELEVANT_TAGS = AI_TAGS | SWE_TAGS | STARTUP_TAGS

# Roles to skip — non-tech generic listings (expanded list)
SKIP_KEYWORDS = {
    "administrative assistant", "executive assistant", "virtual assistant",
    "proposal manager", "scl agent", "scrum master", "expression of interest",
    "transition of candidate", "hr manager", "recruiter", "sales representative",
    "data entry", "customer service", "content moderator", "social media manager",
    "copywriter", "translator", "transcriber", "bookkeeper", "accountant",
    "graphic designer", "video editor", "photographer", "real estate",
    "teacher", "tutor", "nurse", "medical", "dental", "pharmacy",
    "warehouse", "driver", "delivery", "janitor", "cleaner",
    "receptionist", "secretary", "clerk", "cashier", "barista",
    "police", "security guard", "dispatcher", "call center",
    "analista de", "assistente de", "auxiliar", "técnico de",  # Portuguese junk
    "employee ii", "employee iii",
}

# Title must contain at least one of these to be considered tech-relevant
TECH_SIGNAL_WORDS = {
    "engineer", "developer", "programming", "software", "data", "machine learning",
    "artificial intelligence", "ai", "ml", "devops", "sre", "cloud", "backend",
    "frontend", "full-stack", "fullstack", "python", "java", "golang", "rust",
    "typescript", "react", "node", "kubernetes", "docker", "aws", "gcp", "azure",
    "deep learning", "nlp", "computer vision", "llm", "generative", "research",
    "analyst", "scientist", "architect", "infrastructure", "platform", "security",
    "intern", "internship",
}


def _is_relevant(position: str, tags: set[str], text: str) -> bool:
    """Return True only if the job is clearly tech/AI/ML relevant."""
    # Hard skip on non-tech roles
    if any(skip in position for skip in SKIP_KEYWORDS):
        return False

    # Must match relevant tags OR contain tech signal words
    if ALL_RELEVANT_TAGS & tags:
        return True
    if any(tag in text for tag in ALL_RELEVANT_TAGS):
        return True
    if any(word in position for word in TECH_SIGNAL_WORDS):
        return True

    return False


async def fetch_remoteok(client: httpx.AsyncClient, lookback_days: int) -> list[NormalizedItem]:
    response = await client.get(REMOTEOK_URL, headers={"User-Agent": "ai-opportunity-agent/0.2"})
    response.raise_for_status()
    payload = response.json()
    jobs = payload[1:] if isinstance(payload, list) else []
    cutoff = now_utc() - timedelta(days=lookback_days)

    items: list[NormalizedItem] = []
    skipped = 0
    for job in jobs:
        tags = {str(tag).lower() for tag in job.get("tags", [])}
        position = str(job.get("position", "")).lower()
        company = str(job.get("company", "")).lower()
        description = str(job.get("description", "")).lower()
        text = f"{position} {description} {company}"

        if not _is_relevant(position, tags, text):
            skipped += 1
            continue

        # Determine category
        if any(t in tags or t in position for t in AI_TAGS):
            category = "internship" if "intern" in position else "opportunity"
        elif "intern" in position:
            category = "internship"
        else:
            category = "opportunity"

        # Build clean summary
        company_name = job.get("company", "Unknown company")
        summary_parts = [f"Remote {position.title()} role at {company_name}"]
        if tags & AI_TAGS:
            summary_parts.append("AI/ML focused")
        if "intern" in position:
            summary_parts.append("Internship")

        item = normalize_item(
            title=f"{job.get('position', 'AI role')} at {job.get('company', 'Unknown company')}",
            url=job.get("url", ""),
            source="RemoteOK",
            timestamp=job.get("date", ""),
            raw_text=". ".join(summary_parts),
            tier=2,
            category=category,
        )
        if item and item.timestamp >= cutoff:
            items.append(item)

    LOGGER.info("Fetched %s RemoteOK AI/ML/SWE opportunities (filtered out %s non-tech)", len(items), skipped)
    return items
