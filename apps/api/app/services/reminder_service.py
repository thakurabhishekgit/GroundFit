"""
Job-link expiry reminders: email when deadline is within REMINDER_HOURS_BEFORE
and the job is not marked applied.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.job_link import JobLink
from app.services.email_service import _ensure_email_file_logger, send_job_expiry_reminder

logger = logging.getLogger("groundfit.email")


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _in_reminder_window(expires_at: datetime, now: datetime, hours_before: int) -> bool:
    exp = _aware(expires_at)
    window_end = now + timedelta(hours=hours_before)
    return now < exp <= window_end


async def _send_one(db: AsyncSession, link: JobLink, now: datetime) -> bool:
    user = link.user
    if user is None or not user.email:
        result = await db.execute(
            select(JobLink)
            .options(selectinload(JobLink.user))
            .where(JobLink.id == link.id)
        )
        link = result.scalar_one()
        user = link.user
    if user is None or not user.email:
        logger.warning("[REMINDER-SKIP] link=%s missing user email", link.id)
        return False

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
        logger.info(
            "[REMINDER-OK] link=%s to=%s subject=%r",
            link.id,
            user.email,
            link.subject,
        )
        return True
    logger.warning(
        "[REMINDER-FAIL] link=%s to=%s — left reminder_sent_at null for retry",
        link.id,
        user.email,
    )
    return False


async def maybe_send_reminder_for_link(db: AsyncSession, link_id: UUID) -> bool:
    """
    Immediately email if this link is in the reminder window (used on create/update).
    Avoids missing short deadlines while waiting for the poll.
    """
    _ensure_email_file_logger()
    settings = get_settings()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(JobLink)
        .options(selectinload(JobLink.user))
        .where(JobLink.id == link_id, JobLink.is_deleted.is_(False))
    )
    link = result.scalar_one_or_none()
    if link is None:
        return False
    if link.applied or link.expires_at is None or link.reminder_sent_at is not None:
        logger.info(
            "[REMINDER-IMMEDIATE] skip id=%s applied=%s expires=%s sent=%s",
            link.id,
            link.applied,
            link.expires_at,
            link.reminder_sent_at,
        )
        return False
    if not _in_reminder_window(link.expires_at, now, settings.reminder_hours_before):
        hours_left = (_aware(link.expires_at) - now).total_seconds() / 3600
        logger.info(
            "[REMINDER-IMMEDIATE] not in window id=%s hours_left=%.2f",
            link.id,
            hours_left,
        )
        return False

    logger.info("[REMINDER-IMMEDIATE] sending id=%s subject=%r", link.id, link.subject)
    ok = await _send_one(db, link, now)
    if ok:
        await db.commit()
        await db.refresh(link)
    return ok


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
        exp = _aware(link.expires_at)  # type: ignore[arg-type]
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
        if await _send_one(db, link, now):
            sent += 1

    if links:
        await db.commit()
    return sent


async def reminder_poll_loop(stop_event: asyncio.Event) -> None:
    """Background loop started from app lifespan."""
    _ensure_email_file_logger()
    settings = get_settings()
    interval = max(30, settings.reminder_poll_seconds)
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
