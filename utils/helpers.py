"""
helpers.py — General-purpose utilities shared across modules.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ── ID / naming ───────────────────────────────────────────────────────────────

def generate_request_id() -> str:
    """Short unique ID for correlating logs across modules."""
    return uuid.uuid4().hex[:12]


def timestamp_str() -> str:
    """Human-readable timestamp for filenames."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def hash_file(path: str | Path, algo: str = "sha256") -> str:
    """Return hex digest of a file — useful for dedup / caching."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── File helpers ──────────────────────────────────────────────────────────────

def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_delete(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Could not delete %s: %s", path, exc)


def copy_file(src: str | Path, dst_dir: str | Path) -> Path:
    dst = Path(dst_dir) / Path(src).name
    shutil.copy2(src, dst)
    return dst


# ── Async helpers ─────────────────────────────────────────────────────────────

async def async_sleep(seconds: float) -> None:
    """Awaitable sleep — keeps the event loop unblocked."""
    await asyncio.sleep(seconds)


async def run_in_executor(func: Callable, *args: Any) -> Any:
    """Run a synchronous blocking function in a thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


# ── Retry decorator ───────────────────────────────────────────────────────────

def async_retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for async functions.  Retries with exponential back-off.

    Usage:
        @async_retry(max_attempts=3, delay=2, backoff=2)
        async def fragile_call(): ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            attempt = 0
            wait = delay
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, max_attempts, exc
                        )
                        raise
                    logger.warning(
                        "%s attempt %d/%d failed: %s. Retrying in %.1fs…",
                        func.__name__, attempt, max_attempts, exc, wait
                    )
                    await asyncio.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator


# ── Text helpers ──────────────────────────────────────────────────────────────

def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    return text if len(text) <= max_len else text[: max_len - len(suffix)] + suffix


def format_results_message(results: list[dict]) -> str:
    """
    Format extracted PimEyes results into a readable Telegram message.
    Each result dict has: url, title, thumbnail_url.
    """
    if not results:
        return "⚠️ No results found for this image."

    lines = [f"🔍 *Found {len(results)} result(s):*\n"]
    for i, r in enumerate(results, 1):
        title = truncate(r.get("title", "Unknown"), 80)
        url   = r.get("url", "#")
        lines.append(f"{i}. [{title}]({url})")

    return "\n".join(lines)
