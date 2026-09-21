"""
GroundFit FastAPI application entrypoint.

Run (from apps/api):
  uvicorn app.main:app --reload --host 0.0.0.0 --port 7000
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
import app.models  # noqa: F401 — register ORM metadata
from app.services.keepalive_service import keepalive_loop
from app.services.reminder_service import reminder_poll_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Startup: create tables if missing + lightweight column patches +
    reminder loop + optional self keep-alive ping.
    Shutdown: stop background tasks, dispose engine pool.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "ALTER TABLE alignment_runs "
                "ADD COLUMN IF NOT EXISTS match_report_json JSONB"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS welcome_email_sent_at TIMESTAMPTZ"
            )
        )

    stop_event = asyncio.Event()
    reminder_task = asyncio.create_task(reminder_poll_loop(stop_event))
    keepalive_task = asyncio.create_task(keepalive_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        for task in (reminder_task, keepalive_task):
            try:
                await asyncio.wait_for(task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()
        await engine.dispose()


def create_app() -> FastAPI:
    """Application factory — used by uvicorn and tests."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Liveness probe for Render / local checks."""
        return {"status": "ok", "service": settings.app_name}

    @application.get("/ping", tags=["system"])
    async def ping() -> dict[str, str | bool]:
        """
        Keep-alive endpoint for external cron / self-ping.

        Render free: idle spin-down after ~15 minutes with no inbound traffic.
        Hit this at least every 10 minutes from GitHub Actions (or similar)
        so the service stays awake for reminder emails.
        """
        return {
            "status": "ok",
            "pong": True,
            "utc": datetime.now(timezone.utc).isoformat(),
            "service": settings.app_name,
        }

    application.include_router(api_router)
    return application


app = create_app()
