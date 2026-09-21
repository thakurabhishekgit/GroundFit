"""
Lists API — bookmark job links with expiry + applied tracking.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.job_link import JobLink
from app.schemas.job_link import JobLinkCreate, JobLinkOut, JobLinkUpdate
from app.services.reminder_service import dispatch_due_reminders


router = APIRouter(prefix="/lists", tags=["lists"])


@router.get("", response_model=list[JobLinkOut], summary="List my saved job links")
async def list_job_links(user: CurrentUser, db: DbSession) -> list[JobLinkOut]:
    result = await db.execute(
        select(JobLink)
        .where(JobLink.user_id == user.id, JobLink.is_deleted.is_(False))
        .order_by(JobLink.expires_at.asc().nulls_last(), JobLink.created_at.desc())
    )
    return [JobLinkOut.model_validate(row) for row in result.scalars().all()]


@router.post(
    "",
    response_model=JobLinkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a job / link card",
)
async def create_job_link(
    payload: JobLinkCreate,
    user: CurrentUser,
    db: DbSession,
) -> JobLinkOut:
    link = JobLink(
        user_id=user.id,
        subject=payload.subject,
        url=payload.url,
        about=payload.about,
        expires_at=payload.expires_at,
        applied=payload.applied,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return JobLinkOut.model_validate(link)


@router.patch("/{link_id}", response_model=JobLinkOut, summary="Edit a job / link card")
async def update_job_link(
    link_id: UUID,
    payload: JobLinkUpdate,
    user: CurrentUser,
    db: DbSession,
) -> JobLinkOut:
    link = await _get_owned_link(db, user.id, link_id)
    data = payload.model_dump(exclude_unset=True)
    clear_expires = data.pop("clear_expires_at", False)

    expiry_changed = False
    if "expires_at" in data:
        if data["expires_at"] != link.expires_at:
            expiry_changed = True
        link.expires_at = data["expires_at"]
    if clear_expires:
        link.expires_at = None
        expiry_changed = True

    for field in ("subject", "url", "about", "applied"):
        if field in data:
            setattr(link, field, data[field])

    # New deadline → allow a fresh reminder; applied → no reminder needed
    if link.applied:
        link.reminder_sent_at = datetime.now(timezone.utc)
    elif expiry_changed:
        link.reminder_sent_at = None

    link.updated_by_id = user.id
    await db.commit()
    await db.refresh(link)
    return JobLinkOut.model_validate(link)


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job / link card",
)
async def delete_job_link(
    link_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    link = await _get_owned_link(db, user.id, link_id)
    link.is_deleted = True
    link.updated_by_id = user.id
    await db.commit()


@router.post(
    "/email/test",
    summary="Send a test email to the current user (SMTP check)",
)
async def send_test_email_to_me(user: CurrentUser) -> dict[str, str | bool]:
    from app.services.email_service import send_test_email

    ok = await send_test_email(to=user.email, name=user.name)
    return {
        "ok": ok,
        "to": user.email,
        "status": "sent" if ok else "failed_or_disabled — check apps/api/logs/email.log",
    }


@router.post(
    "/reminders/dispatch",
    summary="Cron: send due expiry reminder emails",
)
async def cron_dispatch_reminders(
    db: DbSession,
    x_cron_secret: str | None = Header(default=None, alias="X-Cron-Secret"),
) -> dict[str, int | str]:
    """
    Optional external cron (Render Cron / GitHub Actions).

    Header: X-Cron-Secret: <CRON_SECRET>
    Also runs automatically in-process every REMINDER_POLL_SECONDS.
    """
    settings = get_settings()
    if not settings.cron_secret or x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    sent = await dispatch_due_reminders(db)
    return {"sent": sent, "status": "ok"}


async def _get_owned_link(db: DbSession, user_id: UUID, link_id: UUID) -> JobLink:
    result = await db.execute(
        select(JobLink).where(
            JobLink.id == link_id,
            JobLink.user_id == user_id,
            JobLink.is_deleted.is_(False),
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    return link
