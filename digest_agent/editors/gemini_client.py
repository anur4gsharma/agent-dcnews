from __future__ import annotations

import json
import logging
import re
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

    def generate_json(self, *, system_prompt: str, user_payload: dict[str, Any], fallback: Any) -> Any:
        if self.mock:
            return fallback

        prompt = (
            "Return only valid JSON matching the requested shape. "
            "Do not include markdown fences.\n\n"
            f"Input:\n{json.dumps(user_payload, ensure_ascii=False, default=str)}"
        )
        try:
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
            LOGGER.warning("Gemini call failed; using fallback: %s", exc)
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

