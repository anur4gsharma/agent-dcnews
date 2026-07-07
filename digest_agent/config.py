from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    discord_webhook_url: str | None
    gemini_model: str
    schedule_time: str
    schedule_timezone: str
    digest_lookback_days: int
    database_path: Path
    profile_path: Path
    digests_dir: Path

    @property
    def zoneinfo(self) -> ZoneInfo:
        return ZoneInfo(self.schedule_timezone)


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
        schedule_time=os.getenv("SCHEDULE_TIME", "07:00"),
        schedule_timezone=os.getenv("SCHEDULE_TIMEZONE", "Asia/Kolkata"),
        digest_lookback_days=int(os.getenv("DIGEST_LOOKBACK_DAYS", "7")),
        database_path=PROJECT_ROOT / "digest.db",
        profile_path=PROJECT_ROOT / "profile.json",
        digests_dir=PROJECT_ROOT / "digests",
    )

