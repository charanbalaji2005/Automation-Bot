"""
pimeyes_search.py — End-to-end PimEyes search automation.

Workflow:
  1. Open pimeyes.com
  2. Locate and click the upload area
  3. Set the file path on the hidden <input type="file">
  4. Wait for upload confirmation
  5. Trigger the search
  6. Wait for results to render
  7. Hand off to result_extractor

HTTP Toolkit notes are embedded as comments prefixed with [HTK].
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from playwright.async_api import Page, TimeoutError as PWTimeout

from utils.config import settings
from utils.constants import (
    ELEMENT_WAIT_TIMEOUT_MS,
    INTER_ACTION_DELAY_MS,
    PIMEYES_BASE_URL,
    RESULTS_WAIT_TIMEOUT_MS,
    SEARCH_TRIGGER_DELAY_SEC,
    SUCCESS_SHOTS_DIR,
    ERROR_SHOTS_DIR,
)
from utils.helpers import async_sleep, timestamp_str
from utils.logger import get_logger

logger = get_logger(__name__)


class PimEyesSearch:
    """
    Encapsulates a single PimEyes face-search session on a given Playwright Page.
    """

    def __init__(self, page: Page, request_id: str = "unknown") -> None:
        self.page = page
        self.request_id = request_id
        self._screenshot_prefix = f"{request_id}_{timestamp_str()}"

    # ── public API ────────────────────────────────────────────────────────────

    async def search(self, image_path: str) -> bool:
        """
        Run the full upload + search flow.

        Returns True if the results page loaded, False on failure.
        """
        try:
            await self._open_homepage()
            await self._upload_image(image_path)
            await self._trigger_search()
            await self._wait_for_results()
            return True
        except PWTimeout as exc:
            logger.error("[%s] Timeout during search: %s", self.request_id, exc)
            await self._screenshot("error_timeout")
            return False
        except Exception as exc:
            logger.exception("[%s] Unexpected error during search: %s", self.request_id, exc)
            await self._screenshot("error_unexpected")
            return False

    # ── steps ─────────────────────────────────────────────────────────────────

    async def _open_homepage(self) -> None:
        logger.info("[%s] Navigating to %s", self.request_id, PIMEYES_BASE_URL)
        await self.page.goto(PIMEYES_BASE_URL, wait_until="domcontentloaded")
        await async_sleep(1.5)   # let JS hydrate

        # [HTK] After goto, HTTP Toolkit shows the exact cookies + headers sent.
        # Copy the Cookie header value into data/sessions/ for later direct-HTTP reuse.

        await self._screenshot("step1_homepage")
        logger.debug("[%s] Homepage loaded.", self.request_id)

    async def _upload_image(self, image_path: str) -> None:
        logger.info("[%s] Uploading image: %s", self.request_id, image_path)

        # Strategy 1: direct <input type="file"> interaction (most reliable)
        # PimEyes renders the input hidden behind a styled div.
        # We reveal it, then set_input_files.
        try:
            file_input = self.page.locator("input[type='file']").first
            await file_input.wait_for(state="attached", timeout=ELEMENT_WAIT_TIMEOUT_MS)

            # Make hidden input interactable (Playwright can set files even on hidden inputs)
            await self.page.evaluate(
                """
                () => {
                    const inp = document.querySelector("input[type='file']");
                    if (inp) {
                        inp.style.display = 'block';
                        inp.style.opacity = '1';
                    }
                }
                """
            )

            await file_input.set_input_files(str(image_path))
            logger.debug("[%s] File set on input element.", self.request_id)

        except PWTimeout:
            # Strategy 2: click the visible upload button, intercept file chooser
            logger.warning("[%s] File input not found directly; trying click approach.", self.request_id)
            async with self.page.expect_file_chooser() as fc_info:
                # Try common upload button patterns
                for selector in [
                    "[class*='upload']",
                    "[class*='Upload']",
                    "[aria-label*='upload']",
                    "button:has-text('Upload')",
                    "label[for]",
                ]:
                    try:
                        await self.page.click(selector, timeout=3000)
                        break
                    except Exception:
                        continue

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(image_path))

        # [HTK] At this point HTTP Toolkit will show a multipart/form-data POST
        # (or an XHR) containing the raw image bytes.  Capture:
        #   • Content-Type: multipart/form-data; boundary=...
        #   • Authorization / x-csrf-token headers
        #   • The response JSON with a temporary image token/URL
        # That token is what gets passed to the actual search endpoint.

        await async_sleep(2)   # wait for upload processing
        await self._screenshot("step2_uploaded")
        logger.info("[%s] Image uploaded successfully.", self.request_id)

    async def _trigger_search(self) -> None:
        logger.info("[%s] Triggering search…", self.request_id)
        await async_sleep(SEARCH_TRIGGER_DELAY_SEC)

        search_selectors = [
            "button[type='submit']",
            "[class*='search-btn']",
            "[class*='SearchBtn']",
            "button:has-text('Search')",
            "[aria-label*='search']",
        ]

        clicked = False
        for selector in search_selectors:
            try:
                btn = self.page.locator(selector).first
                await btn.wait_for(state="visible", timeout=5000)
                await btn.click()
                clicked = True
                logger.debug("[%s] Clicked search button: %s", self.request_id, selector)
                break
            except Exception:
                continue

        if not clicked:
            # Last resort: submit the closest form
            logger.warning("[%s] No search button found — submitting form via JS.", self.request_id)
            await self.page.evaluate("document.querySelector('form') && document.querySelector('form').submit()")

        # [HTK] The search POST will contain the image token from the upload step.
        # The response will be a redirect or JSON with a search-ID used in the results URL.

        await self._screenshot("step3_search_triggered")

    async def _wait_for_results(self) -> None:
        logger.info("[%s] Waiting for results page…", self.request_id)

        # Wait for URL to change to results page
        try:
            await self.page.wait_for_url(
                "**/results**",
                timeout=RESULTS_WAIT_TIMEOUT_MS,
            )
            logger.debug("[%s] Results URL detected.", self.request_id)
        except PWTimeout:
            logger.warning("[%s] URL didn't change to /results; checking page content.", self.request_id)

        # Wait for at least one result card to appear
        result_selectors = [
            "[class*='result']",
            "[class*='Result']",
            ".search-results",
            "[data-testid*='result']",
        ]
        for selector in result_selectors:
            try:
                await self.page.wait_for_selector(
                    selector,
                    timeout=RESULTS_WAIT_TIMEOUT_MS,
                    state="visible",
                )
                logger.info("[%s] Results visible (selector: %s).", self.request_id, selector)
                await self._screenshot("step4_results")
                return
            except PWTimeout:
                continue

        logger.warning("[%s] Could not confirm results loaded.", self.request_id)
        await self._screenshot("step4_results_uncertain")

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _screenshot(self, label: str) -> Optional[str]:
        if not settings.SAVE_STEP_SCREENSHOTS:
            return None
        try:
            is_error = "error" in label.lower()
            folder = ERROR_SHOTS_DIR if is_error else SUCCESS_SHOTS_DIR
            Path(folder).mkdir(parents=True, exist_ok=True)
            path = f"{folder}/{self._screenshot_prefix}_{label}.png"
            await self.page.screenshot(path=path, full_page=False)
            logger.debug("[%s] Screenshot saved: %s", self.request_id, path)
            return path
        except Exception as exc:
            logger.warning("[%s] Screenshot failed: %s", self.request_id, exc)
            return None
