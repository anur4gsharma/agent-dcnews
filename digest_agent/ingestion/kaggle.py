from __future__ import annotations

import asyncio
import csv
import logging
import shutil
from io import StringIO

from digest_agent.ingestion.normalize import NormalizedItem, normalize_item, now_utc


LOGGER = logging.getLogger(__name__)


async def fetch_kaggle_competitions() -> list[NormalizedItem]:
    if not shutil.which("kaggle"):
        LOGGER.info("Kaggle CLI not installed; skipping Kaggle competitions")
        return []

    process = await asyncio.create_subprocess_exec(
        "kaggle",
        "competitions",
        "list",
        "--csv",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        LOGGER.warning("Kaggle CLI failed: %s", stderr.decode("utf-8", errors="ignore").strip())
        return []

    reader = csv.DictReader(StringIO(stdout.decode("utf-8", errors="ignore")))
    items: list[NormalizedItem] = []
    for row in reader:
        title = row.get("Title") or row.get("title") or ""
        ref = row.get("ref") or row.get("Ref") or ""
        if not title:
            continue

        # Build clean summary
        reward = row.get("Reward") or row.get("reward", "")
        deadline = row.get("Deadline") or row.get("deadline", "Unknown")
        summary_parts = []
        if reward:
            summary_parts.append(f"Reward: {reward}")
        if deadline and deadline != "Unknown":
            summary_parts.append(f"Deadline: {deadline}")
        raw_text = ". ".join(summary_parts) if summary_parts else title

        item = normalize_item(
            title=title,
            url=f"https://www.kaggle.com/competitions/{ref}" if ref else "https://www.kaggle.com/competitions",
            source="Kaggle",
            timestamp=now_utc(),
            raw_text=raw_text,
            tier=2,
            category="competition",
            deadline=deadline,
        )
        if item:
            items.append(item)

    LOGGER.info("Fetched %s Kaggle competitions", len(items))
    return items[:20]
