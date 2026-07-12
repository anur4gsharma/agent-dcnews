from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Iterable

from rapidfuzz import fuzz


@dataclass(frozen=True)
class NormalizedItem:
    title: str
    url: str
    source: str
    timestamp: datetime
    raw_text: str
    tier: int
    category: str = ""
    deadline: str = "Unknown"

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "raw_text": self.raw_text,
            "tier": self.tier,
            "category": self.category,
            "deadline": self.deadline,
        }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return " ".join(text.split())


def parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                dt = now_utc()
    else:
        dt = now_utc()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_item(
    *,
    title: str,
    url: str,
    source: str,
    timestamp: object,
    raw_text: str,
    tier: int,
    category: str = "",
    deadline: str = "Unknown",
) -> NormalizedItem | None:
    title = strip_html(" ".join((title or "").split()))
    url = (url or "").strip()
    if not title or not url:
        return None
    return NormalizedItem(
        title=title,
        url=url,
        source=source,
        timestamp=parse_datetime(timestamp),
        raw_text=strip_html(" ".join((raw_text or title).split()))[:3000],
        tier=tier,
        category=category,
        deadline=deadline,
    )


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()


def dedupe_items(items: Iterable[NormalizedItem], title_threshold: int = 92) -> list[NormalizedItem]:
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    deduped: list[NormalizedItem] = []

    for item in sorted(items, key=lambda x: x.timestamp, reverse=True):
        digest = url_hash(item.url)
        if digest in seen_urls:
            continue
        if any(fuzz.token_set_ratio(item.title, title) >= title_threshold for title in seen_titles):
            continue
        seen_urls.add(digest)
        seen_titles.append(item.title)
        deduped.append(item)

    return deduped
