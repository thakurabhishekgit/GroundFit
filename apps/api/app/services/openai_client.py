"""
OpenAI client wrapper used by extract / align / verify agents.
"""

import json
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import get_settings


def get_openai_client() -> AsyncOpenAI:
    """Build an AsyncOpenAI client from settings."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def chat_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Call the configured chat model and parse a JSON object response.

    Uses response_format json_object when the model supports it.
    Falls back to stripping markdown fences if needed.
    """
    settings = get_settings()
    client = get_openai_client()

    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content or "{}"
    return _parse_json_content(content)


async def chat_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.3,
) -> str:
    """Call the chat model and return plain text (e.g. LaTeX fragment)."""
    settings = get_settings()
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=settings.openai_chat_model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def _parse_json_content(content: str) -> dict[str, Any]:
    """Parse model output into a dict; tolerate optional ```json fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # drop first/last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Model JSON root must be an object")
    return data
