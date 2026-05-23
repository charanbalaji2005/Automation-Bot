"""
config.py — Typed configuration loaded from environment / .env file.

All secrets live in the .env file; this module exposes a single
`settings` singleton imported everywhere else.

Usage:
    from utils.config import settings
    print(settings.TELEGRAM_BOT_TOKEN)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.constants import (
    API_HOST,
    API_PORT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_RETRY_BACKOFF,
    MAX_IMAGE_SIZE_MB,
    UPLOADS_DIR,
    SCREENSHOTS_DIR,
    LOGS_DIR,
    COOKIES_DIR,
    SESSIONS_DIR,
    CACHE_DIR,
)


class Settings(BaseSettings):
    """
    All configurable values.  Pydantic reads these from:
      1. Environment variables (highest priority)
      2. .env file in the project root
      3. Defaults defined below
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Telegram ─────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    TELEGRAM_WEBHOOK_URL: Optional[str] = None   # set for webhook mode

    # ── FastAPI ───────────────────────────────────────────────────────────────
    API_HOST: str = API_HOST
    API_PORT: int = API_PORT
    API_SECRET_KEY: str = "change-me-in-production"

    # ── Browser ───────────────────────────────────────────────────────────────
    HEADLESS: bool = True            # False = open visible browser window
    SLOW_MO_MS: int = 50             # ms between Playwright actions (human feel)
    BROWSER_TIMEOUT_MS: int = 30_000

    # ── Proxy (optional, helps avoid blocks) ─────────────────────────────────
    # HTTP Toolkit note: set PROXY_SERVER to route traffic through the toolkit
    # for live header capture during development.
    PROXY_SERVER: Optional[str] = None     # e.g. "http://127.0.0.1:8080"
    PROXY_USERNAME: Optional[str] = None
    PROXY_PASSWORD: Optional[str] = None

    # ── Retry ─────────────────────────────────────────────────────────────────
    MAX_RETRIES: int = DEFAULT_MAX_RETRIES
    RETRY_DELAY: float = DEFAULT_RETRY_DELAY
    RETRY_BACKOFF: float = DEFAULT_RETRY_BACKOFF

    # ── Image ─────────────────────────────────────────────────────────────────
    MAX_IMAGE_SIZE_MB: int = MAX_IMAGE_SIZE_MB

    # ── Paths ─────────────────────────────────────────────────────────────────
    UPLOADS_DIR: str = UPLOADS_DIR
    SCREENSHOTS_DIR: str = SCREENSHOTS_DIR
    LOGS_DIR: str = LOGS_DIR
    COOKIES_DIR: str = COOKIES_DIR
    SESSIONS_DIR: str = SESSIONS_DIR
    CACHE_DIR: str = CACHE_DIR

    # ── Feature flags ─────────────────────────────────────────────────────────
    SAVE_STEP_SCREENSHOTS: bool = True    # save debug screenshots per step
    ENABLE_SESSION_PERSISTENCE: bool = True
    DEBUG: bool = False

    @field_validator(
        "UPLOADS_DIR", "SCREENSHOTS_DIR", "LOGS_DIR",
        "COOKIES_DIR", "SESSIONS_DIR", "CACHE_DIR",
        mode="before",
    )
    @classmethod
    def _ensure_dir(cls, v: str) -> str:
        Path(v).mkdir(parents=True, exist_ok=True)
        return v


# ── module-level singleton ────────────────────────────────────────────────────
settings = Settings()
