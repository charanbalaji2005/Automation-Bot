"""
session_manager.py — Persists browser cookies between runs.

PimEyes may set session cookies after the first visit.  Reusing them:
  • reduces bot-detection risk (looks like a returning user)
  • may skip CAPTCHA on repeat searches

[HTK] HTTP Toolkit captures the Set-Cookie headers on the initial GET.
Copy those values into data/cookies/pimeyes_cookies.json to bootstrap a
session without even opening the browser once.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

from utils.config import settings
from utils.constants import COOKIE_FILE_NAME, SESSION_MAX_AGE_H
from utils.logger import get_logger

logger = get_logger(__name__)

_COOKIE_PATH = Path(settings.COOKIES_DIR) / COOKIE_FILE_NAME
_META_PATH   = Path(settings.COOKIES_DIR) / "meta.json"


class SessionManager:
    """Load / save / expire Playwright cookie state."""

    def __init__(self, cookie_path: Optional[str] = None) -> None:
        self._cookie_path = Path(cookie_path) if cookie_path else _COOKIE_PATH
        self._meta_path   = _META_PATH
        self._cookie_path.parent.mkdir(parents=True, exist_ok=True)

    # ── public ────────────────────────────────────────────────────────────────

    def has_valid_session(self) -> bool:
        if not self._cookie_path.exists():
            return False
        if not self._meta_path.exists():
            return False
        meta = self._load_meta()
        age_h = (time.time() - meta.get("saved_at", 0)) / 3600
        if age_h > SESSION_MAX_AGE_H:
            logger.info("Session expired (age=%.1f h > %d h limit).", age_h, SESSION_MAX_AGE_H)
            return False
        return True

    def load_cookies(self) -> List[dict]:
        """Return stored cookies, or empty list if none / expired."""
        if not self.has_valid_session():
            return []
        try:
            data = json.loads(self._cookie_path.read_text())
            logger.info("Loaded %d cookies from disk.", len(data))
            return data
        except Exception as exc:
            logger.warning("Failed to load cookies: %s", exc)
            return []

    def save_cookies(self, cookies: List[dict]) -> None:
        try:
            self._cookie_path.write_text(json.dumps(cookies, indent=2))
            self._save_meta({"saved_at": time.time(), "count": len(cookies)})
            logger.info("Saved %d cookies to disk.", len(cookies))
        except Exception as exc:
            logger.warning("Failed to save cookies: %s", exc)

    def clear(self) -> None:
        for p in (self._cookie_path, self._meta_path):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        logger.info("Session cleared.")

    # ── internals ─────────────────────────────────────────────────────────────

    def _load_meta(self) -> dict:
        try:
            return json.loads(self._meta_path.read_text())
        except Exception:
            return {}

    def _save_meta(self, meta: dict) -> None:
        self._meta_path.write_text(json.dumps(meta, indent=2))
