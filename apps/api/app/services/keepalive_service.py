"""
Keep-alive pings for hosts that sleep on idle (Render free web services).

Render free: spins down after ~15 minutes with no inbound HTTP.
Cold start ~1 minute when the next request arrives.

Self-ping (this loop) only runs while the process is already awake — it resets
the idle timer by hitting our own /ping. If the service is already asleep,
only an EXTERNAL scheduler (GitHub Actions / Render Cron) can wake it.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

logger = logging.getLogger("groundfit.keepalive")


async def keepalive_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    if not settings.keepalive_enabled:
        logger.info("[KEEPALIVE] disabled (KEEPALIVE_ENABLED=false)")
        return

    base = (settings.public_api_url or "").rstrip("/")
    if not base:
        logger.warning(
            "[KEEPALIVE] enabled but PUBLIC_API_URL is empty — skipping self-ping"
        )
        return

    interval = max(60, settings.keepalive_interval_seconds)
    ping_url = f"{base}/ping"
    logger.info("[KEEPALIVE] self-ping every %ss → %s", interval, ping_url)

    # First ping after a short delay so startup can finish
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=15)
        return
    except asyncio.TimeoutError:
        pass

    while not stop_event.is_set():
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.get(ping_url)
            logger.info(
                "[KEEPALIVE] ping status=%s at=%s",
                res.status_code,
                datetime.now(timezone.utc).isoformat(),
            )
        except Exception:  # noqa: BLE001
            logger.exception("[KEEPALIVE] ping failed url=%s", ping_url)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue

    logger.info("[KEEPALIVE] stopped")
