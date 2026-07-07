from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PROFILE = {
    "interests": ["deep learning fundamentals", "agentic systems", "open-source ML tooling"],
    "skill_level": "intermediate",
    "sent_headlines_last_7_days": [],
    "feedback_log": [],
}


def load_profile(path: Path) -> dict:
    if not path.exists():
        save_profile(path, DEFAULT_PROFILE)
        return dict(DEFAULT_PROFILE)
    with path.open("r", encoding="utf-8") as handle:
        profile = json.load(handle)
    merged = dict(DEFAULT_PROFILE)
    merged.update(profile)
    return merged


def save_profile(path: Path, profile: dict) -> None:
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_profile_after_digest(path: Path, profile: dict, digest: dict) -> dict:
    new_headlines = [item["title"] for item in digest.get("top_news", [])]
    new_headlines += [item["title"] for item in digest.get("top_opportunities", [])]
    existing = profile.get("sent_headlines_last_7_days", [])
    profile["sent_headlines_last_7_days"] = (new_headlines + existing)[:100]
    save_profile(path, profile)
    return profile

