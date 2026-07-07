from __future__ import annotations

from datetime import date

from digest_agent.editors.chief_editor import run_chief_editor
from digest_agent.editors.desk_editors import run_opportunities_editor, run_tech_news_editor
from digest_agent.editors.gemini_client import GeminiEditorClient
from digest_agent.editors.wire_editor import run_wire_editor
from digest_agent.ingestion.normalize import NormalizedItem


def run_editor_pipeline(
    *,
    api_key: str | None,
    model: str,
    items: list[NormalizedItem],
    sentiment_items: list[dict],
    profile: dict,
    digest_date: date,
    mock: bool = False,
) -> dict:
    client = GeminiEditorClient(api_key=api_key, model=model, mock=mock)
    wire_items = run_wire_editor(client, items, profile.get("sent_headlines_last_7_days", []))
    tech_candidates = run_tech_news_editor(client, wire_items)
    opportunity_candidates = run_opportunities_editor(client, wire_items, profile)
    return run_chief_editor(
        client,
        tech_candidates=tech_candidates,
        opportunity_candidates=opportunity_candidates,
        sentiment_items=sentiment_items,
        digest_date=digest_date,
    )

