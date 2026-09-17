"""
Application settings loaded from environment / .env.

All secrets stay in env — never hardcode API keys here.
"""

from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# apps/api/app/core/config.py → repo root is parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILES = (
    str(_REPO_ROOT / ".env"),
    ".env",
)


class Settings(BaseSettings):
    """
    Central config for API process.

    Values resolve from process env first, then repo-root `.env`.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "GroundFit API"
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = True
    port: int = Field(default=7000, alias="PORT")
    frontend_url: str = Field(default="http://localhost:2000", alias="FRONTEND_URL")
    cors_origins: str = Field(default="http://localhost:2000", alias="CORS_ORIGINS")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/groundfit",
        alias="DATABASE_URL",
    )

    # --- Auth ---
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- OpenAI ---
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o-mini", alias="OPENAI_CHAT_MODEL")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """
        Normalize Neon/libpq URLs for SQLAlchemy asyncpg.

        - postgresql:// → postgresql+asyncpg://
        - Drop libpq-only params (sslmode, channel_binding) that crash asyncpg
        - Map SSL to asyncpg's `ssl=require` query flag
        """
        if not value:
            return value

        url = value.strip()
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        elif url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]

        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        sslmode = (params.pop("sslmode", "") or "").lower()
        params.pop("channel_binding", None)

        # Neon / managed Postgres almost always need TLS
        host = (parsed.hostname or "").lower()
        needs_ssl = (
            sslmode in {"require", "verify-ca", "verify-full", "prefer"}
            or "neon.tech" in host
            or params.get("ssl", "").lower() in {"1", "true", "require"}
        )
        if needs_ssl:
            params["ssl"] = "require"
        else:
            params.pop("ssl", None)

        return urlunparse(parsed._replace(query=urlencode(params)))

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton for FastAPI Depends."""
    return Settings()
