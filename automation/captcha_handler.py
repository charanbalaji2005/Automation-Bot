"""
captcha_handler.py — CAPTCHA detection and handling.

PimEyes occasionally serves hCaptcha or Cloudflare Turnstile challenges.
This module detects them and provides hooks for:
  1. Manual solving (pause + notify the operator)
  2. 2captcha / CapSolver API integration
  3. Rotating proxy / user-agent to avoid the challenge entirely

[HTK] HTTP Toolkit can reveal the CAPTCHA challenge parameters
(sitekey, action, cdata) from the page JS — useful for headless solvers.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from playwright.async_api import Page

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Common CAPTCHA frame patterns
_CAPTCHA_SELECTORS = [
    "iframe[src*='hcaptcha']",
    "iframe[src*='recaptcha']",
    "iframe[src*='turnstile']",
    "[class*='captcha']",
    "[id*='captcha']",
    "div.h-captcha",
    "div.g-recaptcha",
]


async def detect_captcha(page: Page) -> Optional[str]:
    """
    Check whether the current page has a CAPTCHA challenge.

    Returns:
        'hcaptcha'   | 'recaptcha' | 'turnstile' | None
    """
    for sel in _CAPTCHA_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el:
                src = await el.get_attribute("src") or sel
                kind = _classify(src)
                logger.warning("CAPTCHA detected: %s (selector=%s)", kind, sel)
                return kind
        except Exception:
            continue
    return None


async def handle_captcha(page: Page, kind: str) -> bool:
    """
    Attempt to solve or bypass a detected CAPTCHA.

    Returns True if the challenge appears to have been cleared.

    Extend this method with a real solver (2captcha, CapSolver, etc.)
    using the API keys from settings.
    """
    logger.info("Handling CAPTCHA type: %s", kind)

    # ── Option 1: wait and see (sometimes CAPTCHAs auto-dismiss) ─────────────
    await asyncio.sleep(3)
    if not await detect_captcha(page):
        logger.info("CAPTCHA disappeared on its own.")
        return True

    # ── Option 2: placeholder for 2captcha integration ───────────────────────
    # solver_api_key = settings.CAPTCHA_SOLVER_API_KEY  # add to .env + config
    # solution = await solve_with_2captcha(page, kind, solver_api_key)
    # if solution:
    #     await inject_solution(page, solution)
    #     return True

    # ── Option 3: alert operator and wait (headful mode) ─────────────────────
    if not settings.HEADLESS:
        logger.warning("CAPTCHA requires manual solving. Waiting 120 s…")
        await asyncio.sleep(120)
        return not await detect_captcha(page)

    logger.error("Cannot solve CAPTCHA in headless mode without a solver API key.")
    return False


def _classify(src: str) -> str:
    if "hcaptcha" in src:
        return "hcaptcha"
    if "recaptcha" in src:
        return "recaptcha"
    if "turnstile" in src:
        return "turnstile"
    return "unknown"
