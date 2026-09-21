"""
Transactional email via SMTP.

Skips when EMAIL_ENABLED is false or SMTP is incomplete.
Writes every attempt to logs/email.log for debugging.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger("groundfit.email")

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_email_file_ready = False


def _ensure_email_file_logger() -> None:
    global _email_file_ready
    if _email_file_ready:
        return
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            _LOG_DIR / "email.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        )
        handler.setLevel(logging.INFO)
        # Avoid duplicate handlers on reload
        if not any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", "").endswith("email.log")
            for h in logger.handlers
        ):
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = True  # also show in uvicorn console
        _email_file_ready = True
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Could not set up email.log")


def email_configured() -> bool:
    settings = get_settings()
    if not settings.email_enabled:
        return False
    return bool(
        settings.smtp_host
        and settings.smtp_from
        and settings.smtp_user
        and settings.smtp_password
    )


def _send_sync(*, to: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
    _ensure_email_file_logger()
    settings = get_settings()
    ts = datetime.now(timezone.utc).isoformat()

    if not settings.email_enabled:
        logger.warning(
            "[SKIP] EMAIL_ENABLED=false to=%s subject=%r at=%s", to, subject, ts
        )
        return False
    if not email_configured():
        logger.warning(
            "[SKIP] SMTP incomplete (need HOST/FROM/USER/PASSWORD) to=%s subject=%r at=%s",
            to,
            subject,
            ts,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    password = (settings.smtp_password or "").replace(" ", "")

    try:
        logger.info(
            "[TRY] host=%s port=%s tls=%s ssl=%s user=%s to=%s subject=%r",
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_tls,
            settings.smtp_ssl,
            settings.smtp_user,
            to,
            subject,
        )
        if settings.smtp_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.login(settings.smtp_user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                smtp.login(settings.smtp_user, password)
                smtp.send_message(msg)
        logger.info("[OK] Email sent to=%s subject=%r at=%s", to, subject, ts)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "[FAIL] Email to=%s subject=%r error=%s at=%s", to, subject, exc, ts
        )
        return False


async def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send email off the event loop (smtplib is blocking)."""
    return await asyncio.to_thread(
        _send_sync,
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


async def send_welcome_email(*, to: str, name: Optional[str]) -> bool:
    display = (name or "").strip() or "there"
    settings = get_settings()
    app_url = settings.frontend_url.rstrip("/")
    subject = "Welcome to GroundFit"
    text = (
        f"Hi {display},\n\n"
        "Welcome to GroundFit — evidence-based resume alignment.\n\n"
        "Next steps:\n"
        "1) Paste your experience context and confirm your skill graph\n"
        "2) Align a resume against a job description (Strict or Deliberate)\n"
        "3) Use Lists to bookmark jobs and get expiry reminders\n\n"
        f"Open the app: {app_url}/app\n\n"
        "— GroundFit\n"
    )
    html = f"""
    <p>Hi {display},</p>
    <p>Welcome to <strong>GroundFit</strong> — evidence-based resume alignment.</p>
    <p>Next steps:</p>
    <ol>
      <li>Paste your experience context and confirm your skill graph</li>
      <li>Align a resume against a job description (Strict or Deliberate)</li>
      <li>Use Lists to bookmark jobs and get expiry reminders</li>
    </ol>
    <p><a href="{app_url}/app">Open GroundFit</a></p>
    <p>— GroundFit</p>
    """
    return await send_email(to=to, subject=subject, text_body=text, html_body=html)


async def send_job_expiry_reminder(
    *,
    to: str,
    name: Optional[str],
    subject_line: str,
    url: str,
    about: Optional[str],
    expires_at_iso: str,
) -> bool:
    display = (name or "").strip() or "there"
    settings = get_settings()
    lists_url = f"{settings.frontend_url.rstrip('/')}/app/lists"
    mail_subject = f"Reminder: {subject_line} expires soon"
    about_line = f"\nAbout: {about}\n" if about else "\n"
    text = (
        f"Hi {display},\n\n"
        f"You haven't marked this job as applied yet, and it expires within ~12 hours.\n\n"
        f"Title: {subject_line}\n"
        f"Link: {url}\n"
        f"Expires: {expires_at_iso}\n"
        f"{about_line}"
        f"Open Lists: {lists_url}\n\n"
        "Mark it Applied if you're done, or apply before it expires.\n\n"
        "— GroundFit\n"
    )
    about_html = f"<p>{about}</p>" if about else ""
    html = f"""
    <p>Hi {display},</p>
    <p>You haven't marked this job as <strong>applied</strong> yet, and it expires within ~12 hours.</p>
    <p><strong>{subject_line}</strong><br/>
    <a href="{url}">{url}</a><br/>
    Expires: {expires_at_iso}</p>
    {about_html}
    <p><a href="{lists_url}">Open Lists</a></p>
    <p>— GroundFit</p>
    """
    return await send_email(to=to, subject=mail_subject, text_body=text, html_body=html)


async def send_test_email(*, to: str, name: Optional[str]) -> bool:
    display = (name or "").strip() or "there"
    return await send_email(
        to=to,
        subject="GroundFit test email",
        text_body=(
            f"Hi {display},\n\n"
            "This is a test email from GroundFit SMTP settings.\n"
            "If you received this, email delivery is working.\n\n"
            "— GroundFit\n"
        ),
        html_body=(
            f"<p>Hi {display},</p>"
            "<p>This is a <strong>test email</strong> from GroundFit SMTP settings.</p>"
            "<p>If you received this, email delivery is working.</p>"
            "<p>— GroundFit</p>"
        ),
    )
