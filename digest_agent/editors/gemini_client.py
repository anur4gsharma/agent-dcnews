from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from google import genai
from google.genai import types


LOGGER = logging.getLogger(__name__)


class GeminiEditorClient:
    def __init__(self, *, api_key: str | None, model: str, mock: bool = False) -> None:
        self.api_key = api_key
        self.model = model
        self.mock = mock or not api_key
        self._client = None if self.mock else genai.Client(api_key=api_key)
        self._quota_exhausted = False
        self._call_count = 0

    def generate_json(self, *, system_prompt: str, user_payload: dict[str, Any], fallback: Any) -> Any:
        if self.mock or self._quota_exhausted:
            if self._quota_exhausted:
                LOGGER.debug("Skipping Gemini call (quota exhausted), using fallback")
            return fallback

        prompt = (
            "Return only valid JSON matching the requested shape. "
            "Do not include markdown fences.\n\n"
            f"Input:\n{json.dumps(user_payload, ensure_ascii=False, default=str)}"
        )

        # Retry with backoff for rate limits
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                self._call_count += 1
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                return _parse_json(response.text)
            except Exception as exc:  # noqa: BLE001
                error_str = str(exc)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

                if is_rate_limit and "limit: 0" in error_str:
                    # Daily quota fully exhausted — no point retrying
                    LOGGER.warning("Gemini daily quota exhausted; all remaining calls will use fallback")
                    self._quota_exhausted = True
                    return fallback

                if is_rate_limit and attempt < max_retries:
                    # Per-minute rate limit — wait and retry
                    wait = min(15 * (attempt + 1), 45)
                    LOGGER.info("Gemini rate limited; waiting %ss before retry %s/%s", wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue

                LOGGER.warning("Gemini call failed (attempt %s); using fallback: %s", attempt + 1, exc)
                return fallback

        return fallback


def _parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(1))
        start = min((pos for pos in [text.find("{"), text.find("[")] if pos >= 0), default=-1)
        end = max(text.rfind("}"), text.rfind("]"))
        if start >= 0 and end >= start:
            return json.loads(text[start : end + 1])
        raise
