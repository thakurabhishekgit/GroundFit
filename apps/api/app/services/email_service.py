"""
Transactional email.

Providers (pick via EMAIL_PROVIDER or auto):
  - gmail  → Gmail API over HTTPS (Render-free safe; From = your Gmail)
  - resend → Resend HTTPS API
  - smtp   → classic SMTP (local / paid hosts only; blocked on Render free)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger("groundfit.email")

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_email_file_ready = False
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


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
        if not any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", "").endswith("email.log")
            for h in logger.handlers
        ):
            logger.addHandler(handler)
        if not any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
            for h in logger.handlers
        ):
            sh = logging.StreamHandler()
            sh.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s [email] %(message)s")
            )
            sh.setLevel(logging.INFO)
            logger.addHandler(sh)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        _email_file_ready = True
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Could not set up email.log")


def _log(msg: str, *args: Any, level: int = logging.INFO) -> None:
    _ensure_email_file_logger()
    logger.log(level, msg, *args)
    try:
        print(("[email] " + msg) % args if args else "[email] " + msg, flush=True)
    except Exception:  # noqa: BLE001
        pass


def _gmail_client_id() -> str:
    s = get_settings()
    return (s.gmail_oauth_client_id or s.google_client_id or "").strip()


def _gmail_client_secret() -> str:
    s = get_settings()
    return (s.gmail_oauth_client_secret or s.google_client_secret or "").strip()


def _gmail_sender_address() -> str:
    s = get_settings()
    raw = (s.gmail_sender or s.smtp_user or s.smtp_from or "").strip()
    # "GroundFit <a@b.com>" → a@b.com
    if "<" in raw and ">" in raw:
        return raw.split("<", 1)[1].split(">", 1)[0].strip()
    return raw


def _display_from() -> str:
    s = get_settings()
    if s.smtp_from and "@" in s.smtp_from:
        return s.smtp_from.strip()
    sender = _gmail_sender_address()
    return f"GroundFit <{sender}>" if sender else ""


def email_provider() -> str:
    settings = get_settings()
    raw = (settings.email_provider or "auto").strip().lower()
    if raw in {"gmail", "resend", "smtp"}:
        return raw
    # auto priority: gmail → resend → smtp
    if settings.gmail_refresh_token and _gmail_client_id() and _gmail_client_secret():
        return "gmail"
    if settings.resend_api_key:
        return "resend"
    return "smtp"


def email_configured() -> bool:
    settings = get_settings()
    if not settings.email_enabled:
        return False
    provider = email_provider()
    if provider == "gmail":
        return bool(
            settings.gmail_refresh_token
            and _gmail_client_id()
            and _gmail_client_secret()
            and _gmail_sender_address()
        )
    if provider == "resend":
        return bool(settings.resend_api_key and (settings.resend_from or settings.smtp_from))
    return bool(
        settings.smtp_host
        and settings.smtp_from
        and settings.smtp_user
        and settings.smtp_password
    )


def email_status() -> dict[str, Any]:
    settings = get_settings()
    provider = email_provider()
    notes = {
        "gmail": "Gmail API over HTTPS — From is your Gmail; works on Render free",
        "resend": "Resend HTTPS — needs verified domain for arbitrary recipients",
        "smtp": "SMTP — blocked on Render free (ports 25/465/587)",
    }
    return {
        "email_enabled": settings.email_enabled,
        "provider": provider,
        "configured": email_configured(),
        "from": _display_from() or settings.resend_from or settings.smtp_from or None,
        "gmail_sender": _gmail_sender_address() or None,
        "gmail_refresh_token_set": bool(settings.gmail_refresh_token),
        "resend_key_set": bool(settings.resend_api_key),
        "smtp_host": settings.smtp_host or None,
        "note": notes.get(provider, ""),
    }


def _build_raw_message(
    *,
    sender: str,
    to: str,
    subject: str,
    text_body: str,
    html_body: Optional[str],
) -> str:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")


def _gmail_access_token() -> Optional[str]:
    settings = get_settings()
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": _gmail_client_id(),
                    "client_secret": _gmail_client_secret(),
                    "refresh_token": settings.gmail_refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        if res.status_code >= 400:
            _log(
                "[FAIL] gmail token refresh status=%s body=%s",
                res.status_code,
                res.text[:400],
                level=logging.ERROR,
            )
            return None
        token = res.json().get("access_token")
        if not token:
            _log("[FAIL] gmail token response missing access_token", level=logging.ERROR)
            return None
        return token
    except Exception as exc:  # noqa: BLE001
        _log("[FAIL] gmail token refresh error=%s", exc, level=logging.ERROR)
        return None


def _send_via_gmail(
    *, to: str, subject: str, text_body: str, html_body: Optional[str]
) -> bool:
    sender_display = _display_from()
    sender_email = _gmail_sender_address()
    _log(
        "[TRY] provider=gmail to=%s subject=%r from=%s",
        to,
        subject,
        sender_display,
    )
    access = _gmail_access_token()
    if not access:
        return False
    raw = _build_raw_message(
        sender=sender_display or sender_email,
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={
                    "Authorization": f"Bearer {access}",
                    "Content-Type": "application/json",
                },
                json={"raw": raw},
            )
        if res.status_code >= 400:
            _log(
                "[FAIL] gmail send status=%s body=%s",
                res.status_code,
                res.text[:500],
                level=logging.ERROR,
            )
            return False
        _log("[OK] gmail to=%s id=%s", to, res.json().get("id"))
        return True
    except Exception as exc:  # noqa: BLE001
        _log("[FAIL] gmail send error=%s", exc, level=logging.ERROR)
        return False


def _send_via_resend(
    *, to: str, subject: str, text_body: str, html_body: Optional[str]
) -> bool:
    settings = get_settings()
    from_addr = (settings.resend_from or settings.smtp_from or "").strip()
    payload: dict[str, Any] = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body

    _log("[TRY] provider=resend to=%s subject=%r from=%s", to, subject, from_addr)
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if res.status_code >= 400:
            _log(
                "[FAIL] resend status=%s body=%s",
                res.status_code,
                res.text[:500],
                level=logging.ERROR,
            )
            return False
        _log("[OK] resend to=%s id=%s", to, res.json().get("id"))
        return True
    except Exception as exc:  # noqa: BLE001
        _log("[FAIL] resend error=%s", exc, level=logging.ERROR)
        return False


def _send_via_smtp(
    *, to: str, subject: str, text_body: str, html_body: Optional[str]
) -> bool:
    settings = get_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    password = (settings.smtp_password or "").replace(" ", "")
    _log(
        "[TRY] provider=smtp host=%s port=%s to=%s subject=%r",
        settings.smtp_host,
        settings.smtp_port,
        to,
        subject,
    )
    try:
        if settings.smtp_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=12) as smtp:
                smtp.login(settings.smtp_user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as smtp:
                if settings.smtp_tls:
                    smtp.starttls()
                smtp.login(settings.smtp_user, password)
                smtp.send_message(msg)
        _log("[OK] smtp to=%s subject=%r", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001
        _log(
            "[FAIL] smtp error=%s (Render free blocks SMTP — use EMAIL_PROVIDER=gmail)",
            exc,
            level=logging.ERROR,
        )
        return False


def _send_sync(
    *, to: str, subject: str, text_body: str, html_body: Optional[str] = None
) -> bool:
    _ensure_email_file_logger()
    settings = get_settings()
    ts = datetime.now(timezone.utc).isoformat()

    if not settings.email_enabled:
        _log(
            "[SKIP] EMAIL_ENABLED=false to=%s subject=%r at=%s",
            to,
            subject,
            ts,
            level=logging.WARNING,
        )
        return False
    if not email_configured():
        _log(
            "[SKIP] email not configured (provider=%s) to=%s subject=%r",
            email_provider(),
            to,
            subject,
            level=logging.WARNING,
        )
        return False

    provider = email_provider()
    if provider == "gmail":
        return _send_via_gmail(to=to, subject=subject, text_body=text_body, html_body=html_body)
    if provider == "resend":
        return _send_via_resend(to=to, subject=subject, text_body=text_body, html_body=html_body)
    return _send_via_smtp(to=to, subject=subject, text_body=text_body, html_body=html_body)


async def send_email(
    *,
    to: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
) -> bool:
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
            "This is a test email from GroundFit (Gmail API / configured provider).\n"
            "If you received this, email delivery is working.\n\n"
            "— GroundFit\n"
        ),
        html_body=(
            f"<p>Hi {display},</p>"
            "<p>This is a <strong>test email</strong> from GroundFit.</p>"
            "<p>If you received this, email delivery is working.</p>"
            "<p>— GroundFit</p>"
        ),
    )
