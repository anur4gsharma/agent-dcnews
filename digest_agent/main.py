from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from digest_agent.config import get_settings
from digest_agent.delivery import post_to_discord, write_markdown_archive
from digest_agent.editors import run_editor_pipeline
from digest_agent.ingestion.pipeline import ingest_all
from digest_agent.persistence import DigestDB, load_profile, update_profile_after_digest


LOGGER = logging.getLogger(__name__)


async def run_digest(*, mock: bool = False, dry_run: bool = False) -> dict:
    settings = get_settings()
    db = DigestDB(settings.database_path)
    db.initialize()

    profile = load_profile(settings.profile_path)
    db_headlines = db.get_recent_headlines()
    profile["sent_headlines_last_7_days"] = list(dict.fromkeys(profile.get("sent_headlines_last_7_days", []) + db_headlines))[:100]

    items, sentiment_items = await ingest_all(settings.digest_lookback_days, mock=mock)
    local_now = datetime.now(settings.zoneinfo)
    digest = run_editor_pipeline(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        items=items,
        sentiment_items=sentiment_items,
        profile=profile,
        digest_date=local_now.date(),
        mock=mock,
    )

    archive_path = write_markdown_archive(digest, settings.digests_dir)
    LOGGER.info("Wrote markdown archive to %s", archive_path)
    await post_to_discord(settings.discord_webhook_url, digest, dry_run=dry_run or mock)
    db.record_digest(digest, local_now.date())
    update_profile_after_digest(settings.profile_path, profile, digest)
    LOGGER.info("Digest pipeline complete: %s news, %s opportunities", len(digest["top_news"]), len(digest["top_opportunities"]))
    return digest


def schedule_digest(*, mock: bool = False, dry_run: bool = False) -> None:
    settings = get_settings()
    hour, minute = [int(part) for part in settings.schedule_time.split(":", maxsplit=1)]
    scheduler = BlockingScheduler(timezone=settings.zoneinfo)
    scheduler.add_job(
        lambda: asyncio.run(run_digest(mock=mock, dry_run=dry_run)),
        CronTrigger(day_of_week="sun", hour=hour, minute=minute, timezone=settings.zoneinfo),
        id="weekly_digest",
        replace_existing=True,
    )
    LOGGER.info("Scheduled weekly digest for Sundays at %s %s", settings.schedule_time, settings.schedule_timezone)
    scheduler.start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI/tech weekly digest agent")
    parser.add_argument("--run-now", action="store_true", help="Run the full pipeline once")
    parser.add_argument("--schedule", action="store_true", help="Start the local weekly scheduler")
    parser.add_argument("--mock", action="store_true", help="Use sample data and mock Gemini output")
    parser.add_argument("--dry-run", action="store_true", help="Skip Discord posting")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    args = parse_args()
    if args.run_now:
        asyncio.run(run_digest(mock=args.mock, dry_run=args.dry_run))
    elif args.schedule:
        schedule_digest(mock=args.mock, dry_run=args.dry_run)
    else:
        raise SystemExit("Use --run-now or --schedule")

