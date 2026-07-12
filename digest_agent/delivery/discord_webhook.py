from __future__ import annotations

import logging

import httpx


LOGGER = logging.getLogger(__name__)

CATEGORY_EMOJI = {
    "internship": "💼",
    "hackathon": "🏗️",
    "competition": "🏆",
    "event": "📅",
    "fellowship": "🎓",
    "open_source": "🔓",
    "research": "🔬",
    "opportunity": "✨",
}


async def post_to_discord(webhook_url: str | None, digest: dict, *, dry_run: bool = False) -> None:
    if dry_run or not webhook_url:
        LOGGER.info("Skipping Discord post because dry_run=%s or webhook is missing", dry_run)
        return

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Post News in chunks of 5
        news_items = digest.get("top_news", [])
        if news_items:
            for i in range(0, len(news_items), 5):
                chunk = news_items[i:i + 5]
                title = f"📰 Top News (Part {i//5 + 1})" if len(news_items) > 5 else f"🤖 AI/Tech Weekly Digest — {digest['date']}"
                if i == 0 and len(news_items) > 5:
                    title = f"🤖 AI/Tech Weekly Digest — {digest['date']} (News Part 1)"
                
                embed = {
                    "title": title,
                    "color": 0x2F80ED,
                    "fields": _news_fields(chunk),
                }
                await _send_embeds(client, webhook_url, [embed])

        # 2. Post Opportunities in chunks of 5
        opp_items = digest.get("top_opportunities", [])
        if opp_items:
            for i in range(0, len(opp_items), 5):
                chunk = opp_items[i:i + 5]
                title = f"🚀 Opportunities (Part {i//5 + 1})" if len(opp_items) > 5 else "🚀 Opportunities"
                
                embed = {
                    "title": title,
                    "color": 0x00C853,
                    "fields": _opportunity_fields(chunk),
                }
                await _send_embeds(client, webhook_url, [embed])

        # 3. Post Sentiment
        sentiment = digest.get("sentiment", [])
        if sentiment:
            embed = {
                "title": "💬 Community Pulse",
                "color": 0xFF6B35,
                "description": _sentiment_description(sentiment),
            }
            await _send_embeds(client, webhook_url, [embed])

    LOGGER.info("Posted digest to Discord in multiple chunks to bypass character limits")


async def _send_embeds(client: httpx.AsyncClient, webhook_url: str, embeds: list[dict]) -> None:
    payload = {"embeds": embeds}
    response = await client.post(webhook_url, json=payload)
    response.raise_for_status()


def _news_fields(items: list[dict]) -> list[dict]:
    fields = []
    for item in items:
        name = f"[{_truncate(item['title'], 200)}]({item['url']})"
        value = item["why_it_matters"]
        source = item.get("source", "")
        if source:
            value = f"{value}\n_Source: {source}_"
        fields.append({"name": name, "value": _truncate(value, 800), "inline": False})
    return fields


def _opportunity_fields(items: list[dict]) -> list[dict]:
    fields: list[dict] = []
    for item in items:
        category = item.get("category", "opportunity")
        emoji = CATEGORY_EMOJI.get(category, "✨")
        name = f"{emoji} [{_truncate(item['title'], 200)}]({item['url']})"

        meta_parts = []
        org = item.get("organization", "")
        if org and org != "Unknown":
            meta_parts.append(f"**Org:** {org}")
        mode = item.get("mode", "")
        if mode and mode != "Unknown":
            meta_parts.append(f"**Mode:** {mode}")
        deadline = item.get("deadline", "")
        if deadline and deadline != "Unknown":
            meta_parts.append(f"**Deadline:** {deadline}")
        cost = item.get("cost", "")
        if cost and cost != "Unknown":
            meta_parts.append(f"**Cost:** {cost}")
        difficulty = item.get("difficulty", "")
        if difficulty and difficulty != "Unknown":
            meta_parts.append(f"**Level:** {difficulty}")
        priority = item.get("priority_score", "")
        if priority:
            meta_parts.append(f"**Priority:** {priority}/10")

        meta_line = " · ".join(meta_parts)
        why = item.get("why_it_matters", "")
        value = f"{why}\n{meta_line}" if meta_line else why

        fields.append({"name": name, "value": _truncate(value, 800), "inline": False})
    return fields


def _sentiment_description(items: list[dict]) -> str:
    """Build a compact description for the sentiment embed."""
    lines = ["What the AI/ML community is discussing this week:\n"]
    for item in items[:6]:
        title = _truncate(item.get("title", ""), 80)
        score = item.get("score", 0)
        comments = item.get("comments", 0)
        subreddit = item.get("subreddit", "")
        url = item.get("url", "")
        lines.append(f"⬆ **{score:,}** · 💬 {comments:,} — [{title}]({url}) _(r/{subreddit})_")
    return "\n".join(lines)


def _truncate(value: str, limit: int) -> str:
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[: limit - 1] + "…"
