"""
browser.py — Playwright browser lifecycle manager.

Provides an async context manager that launches / tears down a Chromium
instance with realistic fingerprinting headers so PimEyes doesn't block us.

HTTP Toolkit integration note:
  Set settings.PROXY_SERVER = "http://127.0.0.1:8080" and launch HTTP Toolkit
  on that port to intercept every request the browser makes.  This lets you:
    • capture the exact multipart/form-data upload request
    • identify any CSRF tokens or signed URLs
    • replicate requests without a browser at all (see upload_handler.py)
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from utils.config import settings
from utils.constants import (
    DEFAULT_ACCEPT_LANGUAGE,
    DEFAULT_USER_AGENT,
    DEFAULT_VIEWPORT,
    PAGE_LOAD_TIMEOUT_MS,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """
    Manages a single shared Playwright Chromium instance.

    Usage (preferred — single search):
        async with BrowserManager() as bm:
            page = await bm.new_page()
            ...

    Usage (long-lived service):
        bm = BrowserManager()
        await bm.start()
        page = await bm.new_page()
        ...
        await bm.stop()
    """

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    # ── lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        logger.info("Launching Chromium (headless=%s)", settings.HEADLESS)
        self._playwright = await async_playwright().start()

        launch_kwargs: dict = {
            "headless": settings.HEADLESS,
            "slow_mo": settings.SLOW_MO_MS,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--disable-extensions",
            ],
        }

        # ── optional proxy (use with HTTP Toolkit for traffic capture) ────────
        if settings.PROXY_SERVER:
            logger.info("Routing browser traffic through proxy: %s", settings.PROXY_SERVER)
            proxy_cfg: dict = {"server": settings.PROXY_SERVER}
            if settings.PROXY_USERNAME:
                proxy_cfg["username"] = settings.PROXY_USERNAME
                proxy_cfg["password"] = settings.PROXY_PASSWORD or ""
            launch_kwargs["proxy"] = proxy_cfg

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

        # ── persistent context for cookie / session reuse ─────────────────────
        context_kwargs: dict = {
            "viewport": DEFAULT_VIEWPORT,
            "user_agent": DEFAULT_USER_AGENT,
            "locale": DEFAULT_ACCEPT_LANGUAGE,
            "extra_http_headers": {
                "Accept-Language": DEFAULT_ACCEPT_LANGUAGE,
                # HTTP Toolkit: replace these with headers copied from a real
                # captured session for maximum stealth.
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
            "ignore_https_errors": True,   # needed when MITMing with HTTP Toolkit
        }

        self._context = await self._browser.new_context(**context_kwargs)

        # ── anti-automation detection patch ───────────────────────────────────
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        logger.info("Browser context ready.")

    async def stop(self) -> None:
        logger.info("Closing browser…")
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed.")

    # ── page factory ──────────────────────────────────────────────────────────

    async def new_page(self) -> Page:
        if not self._context:
            raise RuntimeError("BrowserManager not started. Call start() first.")
        page = await self._context.new_page()
        page.set_default_timeout(PAGE_LOAD_TIMEOUT_MS)
        return page

    # ── cookie persistence helpers ────────────────────────────────────────────

    async def save_cookies(self, path: str) -> None:
        if not self._context:
            return
        import json, pathlib
        cookies = await self._context.cookies()
        pathlib.Path(path).write_text(json.dumps(cookies, indent=2))
        logger.debug("Saved %d cookies to %s", len(cookies), path)

    async def load_cookies(self, path: str) -> None:
        import json, pathlib
        p = pathlib.Path(path)
        if not p.exists():
            logger.debug("No cookie file at %s — starting fresh session.", path)
            return
        cookies = json.loads(p.read_text())
        await self._context.add_cookies(cookies)
        logger.debug("Loaded %d cookies from %s", len(cookies), path)

    # ── context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "BrowserManager":
        await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self.stop()


# ── convenience one-shot context manager ─────────────────────────────────────

@asynccontextmanager
async def get_browser_page() -> AsyncGenerator[Page, None]:
    """
    Yield a single ready-to-use Page, then clean up.

    async with get_browser_page() as page:
        await page.goto("https://pimeyes.com/en")
    """
    async with BrowserManager() as bm:
        page = await bm.new_page()
        try:
            yield page
        finally:
            await page.close()
