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

    is_saturday = False
    try:
        from datetime import date
        digest_date = date.fromisoformat(digest.get("date", ""))
        is_saturday = digest_date.weekday() == 5
    except (ValueError, TypeError) as exc:
        LOGGER.debug("Could not parse digest date for Saturday check: %s", exc)

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
        
        fellowship_items = []
        regular_opp_items = []
        if is_saturday:
            for item in opp_items:
                if item.get("category") == "fellowship" or "fellowship" in item.get("title", "").lower():
                    fellowship_items.append(item)
                else:
                    regular_opp_items.append(item)
        else:
            regular_opp_items = opp_items

        if regular_opp_items:
            for i in range(0, len(regular_opp_items), 5):
                chunk = regular_opp_items[i:i + 5]
                title = f"🚀 Opportunities (Part {i//5 + 1})" if len(regular_opp_items) > 5 else "🚀 Opportunities"
                
                embed = {
                    "title": title,
                    "color": 0x00C853,
                    "fields": _opportunity_fields(chunk),
                }
                await _send_embeds(client, webhook_url, [embed])

        # 2b. Post Fellowships if Saturday
        if is_saturday and fellowship_items:
            for i in range(0, len(fellowship_items), 5):
                chunk = fellowship_items[i:i + 5]
                title = f"🎓 Special Saturday Fellowships (Part {i//5 + 1})" if len(fellowship_items) > 5 else "🎓 Special Saturday Fellowships"
                
                embed = {
                    "title": title,
                    "color": 0x9C27B0,
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
        name = _truncate(item['title'], 256)
        value = item["why_it_matters"]
        source = item.get("source", "")
        url = item.get("url", "")
        
        value_parts = [value]
        if source:
            value_parts.append(f"_Source: {source}_")
        if url:
            value_parts.append(f"[Read more]({url})")
            
        fields.append({"name": name, "value": _truncate("\n".join(value_parts), 1024), "inline": False})
    return fields


def _opportunity_fields(items: list[dict]) -> list[dict]:
    fields: list[dict] = []
    for item in items:
        category = item.get("category", "opportunity")
        emoji = CATEGORY_EMOJI.get(category, "✨")
        name = _truncate(f"{emoji} {item['title']}", 256)

        value_parts = []
        why = item.get("why_it_matters", "")
        if why:
            value_parts.append(why)
            
        url = item.get("url", "")
        if url:
            value_parts.append(f"[Apply/Details]({url})")

        fields.append({"name": name, "value": _truncate("\n".join(value_parts), 1024), "inline": False})
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
