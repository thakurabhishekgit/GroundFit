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
from app.services.email_service import _ensure_email_file_logger, send_job_expiry_reminder

logger = logging.getLogger("groundfit.email")


async def dispatch_due_reminders(db: AsyncSession) -> int:
    """
    Find job links in the reminder window and send one email each.

    Window: now < expires_at <= now + REMINDER_HOURS_BEFORE, applied=False,
    reminder_sent_at is null. Only marks sent after a successful SMTP send.
    """
    _ensure_email_file_logger()
    settings = get_settings()
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=settings.reminder_hours_before)

    # Diagnostic: all open (not applied) links with a deadline
    diag = await db.execute(
        select(JobLink)
        .options(selectinload(JobLink.user))
        .where(
            JobLink.is_deleted.is_(False),
            JobLink.applied.is_(False),
            JobLink.expires_at.is_not(None),
        )
    )
    open_links = list(diag.scalars().unique().all())
    for link in open_links:
        exp = link.expires_at
        assert exp is not None
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        hours_left = (exp - now).total_seconds() / 3600
        reasons: list[str] = []
        if link.reminder_sent_at is not None:
            reasons.append(f"already_sent_at={link.reminder_sent_at.isoformat()}")
        if exp <= now:
            reasons.append("expired")
        elif exp > window_end:
            reasons.append(
                f"too_early ({hours_left:.1f}h left; window={settings.reminder_hours_before}h)"
            )
        elif not reasons:
            reasons.append("DUE_NOW")
        logger.info(
            "[REMINDER-SCAN] id=%s subject=%r expires=%s hours_left=%.2f status=%s",
            link.id,
            link.subject,
            exp.isoformat(),
            hours_left,
            "; ".join(reasons),
        )

    result = await db.execute(
        select(JobLink)
        .options(selectinload(JobLink.user))
        .where(
            JobLink.is_deleted.is_(False),
            JobLink.applied.is_(False),
            JobLink.reminder_sent_at.is_(None),
            JobLink.expires_at.is_not(None),
            JobLink.expires_at > now,
            JobLink.expires_at <= window_end,
        )
    )
    links = list(result.scalars().unique().all())
    logger.info(
        "[REMINDER-DISPATCH] due_count=%s email_enabled=%s window_end=%s",
        len(links),
        settings.email_enabled,
        window_end.isoformat(),
    )

    sent = 0
    for link in links:
        user = link.user
        if user is None or not user.email:
            logger.warning("[REMINDER-SKIP] link=%s missing user email", link.id)
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
            logger.info(
                "[REMINDER-OK] link=%s to=%s subject=%r",
                link.id,
                user.email,
                link.subject,
            )
        else:
            logger.warning(
                "[REMINDER-FAIL] link=%s to=%s — left reminder_sent_at null for retry",
                link.id,
                user.email,
            )

    if links:
        await db.commit()
    return sent


async def reminder_poll_loop(stop_event: asyncio.Event) -> None:
    """Background loop started from app lifespan."""
    _ensure_email_file_logger()
    settings = get_settings()
    interval = max(60, settings.reminder_poll_seconds)
    logger.info(
        "[REMINDER-LOOP] started every %ss email_enabled=%s hours_before=%s",
        interval,
        settings.email_enabled,
        settings.reminder_hours_before,
    )
    while not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                n = await dispatch_due_reminders(db)
                logger.info("[REMINDER-LOOP] tick sent=%s", n)
        except Exception:  # noqa: BLE001
            logger.exception("[REMINDER-LOOP] poll failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    logger.info("[REMINDER-LOOP] stopped")
