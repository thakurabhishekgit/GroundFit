"""
Job-link expiry reminders: email ~12h before expires_at when not applied.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.job_link import JobLink
from app.services.email_service import send_job_expiry_reminder

logger = logging.getLogger(__name__)


async def dispatch_due_reminders(db: AsyncSession) -> int:
    """
    Find job links in the reminder window and send one email each.

    Window: expires_at - 12h <= now < expires_at, applied=False, no prior send.
    Returns count of emails attempted (success or fail still marks sent to avoid spam loops
    only on success — failures leave reminder_sent_at null for retry).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(hours=settings.reminder_hours_before)

    result = await db.execute(
        select(JobLink)
        .options(selectinload(JobLink.user))
        .where(
            JobLink.is_deleted.is_(False),
            JobLink.applied.is_(False),
            JobLink.reminder_sent_at.is_(None),
            JobLink.expires_at.is_not(None),
            JobLink.expires_at > window_start,
            JobLink.expires_at <= window_end,
        )
    )
    links = list(result.scalars().unique().all())
    sent = 0
    for link in links:
        user = link.user
        if user is None or not user.email:
            continue
        expires_iso = link.expires_at.isoformat() if link.expires_at else ""
        ok = await send_job_expiry_reminder(
            to=user.email,
            name=user.name,
            subject_line=link.subject,
            url=link.url,
            about=link.about,
            expires_at_iso=expires_iso,
        )
        if ok:
            link.reminder_sent_at = now
            link.updated_by_id = user.id
            sent += 1
        elif not settings.email_enabled:
            # Dev without SMTP: mark as sent so we don't hammer logs every poll
            link.reminder_sent_at = now
            sent += 1

    if links:
        await db.commit()
    return sent


async def reminder_poll_loop(stop_event: asyncio.Event) -> None:
    """Background loop started from app lifespan."""
    settings = get_settings()
    interval = max(60, settings.reminder_poll_seconds)
    logger.info("Reminder poll loop started (every %ss)", interval)
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                n = await dispatch_due_reminders(db)
                if n:
                    logger.info("Dispatch reminders: %s sent", n)
        except Exception:  # noqa: BLE001
            logger.exception("Reminder poll failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    logger.info("Reminder poll loop stopped")
