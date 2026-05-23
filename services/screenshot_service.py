"""
screenshot_service.py — Full-page and element screenshot helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.async_api import Page

from utils.constants import SUCCESS_SHOTS_DIR, ERROR_SHOTS_DIR
from utils.helpers import timestamp_str
from utils.logger import get_logger

logger = get_logger(__name__)


async def capture_full_page(
    page: Page,
    label: str,
    request_id: str = "unknown",
    is_error: bool = False,
) -> Optional[str]:
    folder = ERROR_SHOTS_DIR if is_error else SUCCESS_SHOTS_DIR
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = f"{folder}/{request_id}_{timestamp_str()}_{label}.png"
    try:
        await page.screenshot(path=path, full_page=True)
        logger.debug("Screenshot: %s", path)
        return path
    except Exception as exc:
        logger.warning("Screenshot failed (%s): %s", label, exc)
        return None


async def capture_element(
    page: Page,
    selector: str,
    label: str,
    request_id: str = "unknown",
) -> Optional[str]:
    Path(SUCCESS_SHOTS_DIR).mkdir(parents=True, exist_ok=True)
    path = f"{SUCCESS_SHOTS_DIR}/{request_id}_{timestamp_str()}_{label}.png"
    try:
        el = await page.query_selector(selector)
        if el:
            await el.screenshot(path=path)
            return path
    except Exception as exc:
        logger.warning("Element screenshot failed: %s", exc)
    return None
