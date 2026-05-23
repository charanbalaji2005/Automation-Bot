"""
retry_service.py — Configurable retry wrapper for the search service.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class RetryService:
    """
    Wraps any async callable with configurable retry / back-off.

    Usage:
        svc = RetryService()
        result = await svc.run(image_service.search_from_bytes, image_bytes)
    """

    def __init__(
        self,
        max_retries: Optional[int]   = None,
        delay: Optional[float]       = None,
        backoff: Optional[float]     = None,
    ) -> None:
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.delay       = delay       if delay       is not None else settings.RETRY_DELAY
        self.backoff     = backoff     if backoff     is not None else settings.RETRY_BACKOFF

    async def run(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        attempt = 0
        wait    = self.delay

        while True:
            try:
                result = await func(*args, **kwargs)

                # treat service-level errors as retryable
                if isinstance(result, dict) and not result.get("success"):
                    raise RuntimeError(result.get("error", "Unknown service error"))

                if attempt > 0:
                    logger.info("Succeeded on attempt %d.", attempt + 1)
                return result

            except Exception as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(
                        "Giving up after %d attempt(s): %s", attempt, exc
                    )
                    # Return error dict rather than raising so callers don't need try/except
                    return {
                        "success":    False,
                        "request_id": "unknown",
                        "results":    [],
                        "error":      f"Failed after {attempt} attempt(s): {exc}",
                    }

                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1f s…",
                    attempt, self.max_retries, exc, wait
                )
                await asyncio.sleep(wait)
                wait *= self.backoff
