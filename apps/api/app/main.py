"""
GroundFit FastAPI application entrypoint.

Run (from apps/api):
  uvicorn app.main:app --reload --host 0.0.0.0 --port 7000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import Base, engine
import app.models  # noqa: F401 — register ORM metadata


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Startup: create tables if missing (MVP; switch to Alembic migrations in prod).
    Shutdown: dispose engine pool.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
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

    application.include_router(api_router)
    return application


app = create_app()
