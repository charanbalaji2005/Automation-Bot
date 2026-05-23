"""
validators.py — Input validation utilities.
"""

from __future__ import annotations

import imghdr
import os
from pathlib import Path
from typing import Tuple

from utils.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_IMAGE_TYPES,
    MAX_IMAGE_SIZE_BYTES,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def validate_image_path(path: str | Path) -> Tuple[bool, str]:
    """
    Validate a local image file.

    Returns:
        (True, "ok")          on success
        (False, reason_str)   on failure
    """
    p = Path(path)

    if not p.exists():
        return False, f"File not found: {path}"

    if not p.is_file():
        return False, f"Path is not a file: {path}"

    # ── extension check ───────────────────────────────────────────────────────
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, (
            f"Unsupported extension '{p.suffix}'. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # ── size check ────────────────────────────────────────────────────────────
    size = p.stat().st_size
    if size > MAX_IMAGE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        return False, f"Image too large ({mb:.1f} MB). Maximum allowed: {MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB"

    if size == 0:
        return False, "Image file is empty."

    # ── magic-bytes check (imghdr) ────────────────────────────────────────────
    detected = imghdr.what(str(p))
    if detected is None:
        return False, "Cannot determine image type from file contents (corrupt file?)."

    mime = f"image/{detected}"
    if mime not in ALLOWED_IMAGE_TYPES:
        return False, f"Detected image type '{mime}' is not supported."

    logger.debug("Image validated OK: %s (%d bytes, type=%s)", p.name, size, mime)
    return True, "ok"


def validate_url(url: str) -> bool:
    """Basic URL sanity check."""
    return url.startswith(("http://", "https://")) and len(url) > 10


def sanitize_filename(name: str) -> str:
    """Strip path traversal chars from user-supplied filenames."""
    return "".join(c for c in name if c.isalnum() or c in "-_.")
