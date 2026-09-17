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


def _model_allows_custom_temperature(model: str) -> bool:
    """
    Some chat models only accept the default temperature (1).

    Passing 0 / 0.1 / 0.2 returns HTTP 400 unsupported_value.
    """
    name = (model or "").lower()
    # Restricted families / aliases (extend as needed)
    blocked_markers = ("luna", "o1", "o3", "gpt-5")
    return not any(marker in name for marker in blocked_markers)


def _chat_kwargs(*, temperature: Optional[float]) -> dict[str, Any]:
    """Build create() kwargs; omit temperature when the model forbids it."""
    settings = get_settings()
    kwargs: dict[str, Any] = {"model": settings.openai_chat_model}
    if temperature is not None and _model_allows_custom_temperature(settings.openai_chat_model):
        kwargs["temperature"] = temperature
    return kwargs


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
    client = get_openai_client()

    response = await client.chat.completions.create(
        **_chat_kwargs(temperature=temperature),
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
    client = get_openai_client()
    response = await client.chat.completions.create(
        **_chat_kwargs(temperature=temperature),
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
