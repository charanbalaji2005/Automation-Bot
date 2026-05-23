"""
image_service.py — High-level orchestration service.

Glues together:
  UploadHandler → BrowserManager → PimEyesSearch → result_extractor
  with session persistence and retry logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from automation.browser import BrowserManager
from automation.captcha_handler import detect_captcha, handle_captcha
from automation.pimeyes_search import PimEyesSearch
from automation.result_extractor import extract_results
from automation.session_manager import SessionManager
from automation.upload_handler import UploadHandler
from utils.config import settings
from utils.constants import COOKIES_DIR, COOKIE_FILE_NAME
from utils.helpers import generate_request_id
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageSearchService:
    """
    Orchestrates a complete face-search pipeline:
      1. Save image bytes
      2. Validate
      3. Launch browser (with optional session reuse)
      4. Run PimEyes automation
      5. Handle CAPTCHA if encountered
      6. Extract results
      7. Clean up
    """

    def __init__(self) -> None:
        self._session_mgr = SessionManager()

    async def search_from_bytes(
        self,
        image_bytes: bytes,
        extension: str = ".jpg",
        max_results: int = 10,
    ) -> dict:
        """
        Main entry point.  Returns:
            {
                "success":    bool,
                "request_id": str,
                "results":    List[dict],
                "error":      Optional[str],
            }
        """
        request_id = generate_request_id()
        logger.info("[%s] New search request started.", request_id)

        handler = UploadHandler(request_id=request_id)
        saved   = await handler.save_bytes(image_bytes, extension)

        ok, reason = handler.validate()
        if not ok:
            handler.cleanup()
            logger.warning("[%s] Image validation failed: %s", request_id, reason)
            return self._error(request_id, f"Invalid image: {reason}")

        try:
            results = await self._run_search(str(saved), request_id, max_results)
            return {
                "success":    True,
                "request_id": request_id,
                "results":    results,
                "error":      None,
            }
        except Exception as exc:
            logger.exception("[%s] Search failed: %s", request_id, exc)
            return self._error(request_id, str(exc))
        finally:
            handler.cleanup()

    async def search_from_path(
        self,
        path: str,
        max_results: int = 10,
    ) -> dict:
        request_id = generate_request_id()
        data = Path(path).read_bytes()
        ext  = Path(path).suffix or ".jpg"
        return await self.search_from_bytes(data, ext, max_results)

    # ── internals ─────────────────────────────────────────────────────────────

    async def _run_search(
        self, image_path: str, request_id: str, max_results: int
    ) -> List[dict]:
        cookie_path = str(Path(COOKIES_DIR) / COOKIE_FILE_NAME)

        async with BrowserManager() as bm:
            # ── session reuse ────────────────────────────────────────────────
            if settings.ENABLE_SESSION_PERSISTENCE and self._session_mgr.has_valid_session():
                logger.info("[%s] Reusing stored session.", request_id)
                await bm.load_cookies(cookie_path)

            page = await bm.new_page()

            try:
                # ── run search ───────────────────────────────────────────────
                searcher = PimEyesSearch(page, request_id=request_id)
                success  = await searcher.search(image_path)

                if not success:
                    raise RuntimeError("PimEyes search workflow failed.")

                # ── CAPTCHA check ────────────────────────────────────────────
                captcha_kind = await detect_captcha(page)
                if captcha_kind:
                    solved = await handle_captcha(page, captcha_kind)
                    if not solved:
                        raise RuntimeError(f"Unsolved CAPTCHA ({captcha_kind}).")
                    # re-run search after captcha cleared
                    success = await searcher.search(image_path)
                    if not success:
                        raise RuntimeError("Search failed after CAPTCHA resolution.")

                # ── extract results ──────────────────────────────────────────
                results = await extract_results(page, max_results=max_results)

                # ── persist session ──────────────────────────────────────────
                if settings.ENABLE_SESSION_PERSISTENCE:
                    await bm.save_cookies(cookie_path)

                return results

            finally:
                await page.close()

    @staticmethod
    def _error(request_id: str, message: str) -> dict:
        return {
            "success":    False,
            "request_id": request_id,
            "results":    [],
            "error":      message,
        }
