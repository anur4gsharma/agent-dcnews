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
        item = normalize_item(
            title=title,
            url=f"https://www.kaggle.com/competitions/{ref}" if ref else "https://www.kaggle.com/competitions",
            source="Kaggle",
            timestamp=now_utc(),
            raw_text=f"Reward: {row.get('Reward', '')}. Deadline: {row.get('Deadline', '')}",
            tier=2,
        )
        if item:
            items.append(item)

    LOGGER.info("Fetched %s Kaggle competitions", len(items))
    return items[:20]

