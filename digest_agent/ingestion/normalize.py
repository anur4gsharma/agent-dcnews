from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "raw_text": self.raw_text,
            "tier": self.tier,
        }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


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
) -> NormalizedItem | None:
    title = " ".join((title or "").split())
    url = (url or "").strip()
    if not title or not url:
        return None
    return NormalizedItem(
        title=title,
        url=url,
        source=source,
        timestamp=parse_datetime(timestamp),
        raw_text=" ".join((raw_text or title).split())[:3000],
        tier=tier,
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

