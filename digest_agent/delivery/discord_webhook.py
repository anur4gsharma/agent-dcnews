from __future__ import annotations

import logging

import httpx


LOGGER = logging.getLogger(__name__)


async def post_to_discord(webhook_url: str | None, digest: dict, *, dry_run: bool = False) -> None:
    if dry_run or not webhook_url:
        LOGGER.info("Skipping Discord post because dry_run=%s or webhook is missing", dry_run)
        return

    payload = {
        "embeds": [
            {
                "title": f"AI/Tech Weekly Digest - {digest['date']}",
                "color": 0x2F80ED,
                "fields": _fields("News", digest.get("top_news", []), "source")
                + _fields("Opportunities", digest.get("top_opportunities", []), "type"),
            }
        ]
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
    LOGGER.info("Posted digest to Discord")


def _fields(section: str, items: list[dict], extra_key: str) -> list[dict]:
    fields = [{"name": section, "value": "\u200b", "inline": False}]
    for item in items[:5]:
        name = f"[{_truncate(item['title'], 240)}]({item['url']})"
        extra = item.get(extra_key, "")
        value = item["why_it_matters"]
        if extra:
            value = f"{value}\n_{extra_key.title()}: {extra}_"
        fields.append({"name": name, "value": _truncate(value, 1000), "inline": False})
    return fields


def _truncate(value: str, limit: int) -> str:
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[: limit - 1] + "..."

