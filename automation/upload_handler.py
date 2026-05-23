"""
upload_handler.py — Manages the lifecycle of uploaded images.

Handles saving Telegram downloads to disk, post-search cleanup,
and optional pre-processing (resize / convert) before browser upload.

[HTK] Future direct-HTTP approach:
  Once the PimEyes upload XHR is captured with HTTP Toolkit, replace the
  Playwright upload with a direct httpx multipart POST here.
  Required headers (captured from toolkit):
    • Authorization: Bearer <token>
    • x-api-key: <key>
    • x-csrf-token: <token>
  The response contains an image_token used in the subsequent search call.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

from utils.config import settings
from utils.helpers import generate_request_id, timestamp_str
from utils.logger import get_logger
from utils.validators import validate_image_path

logger = get_logger(__name__)


class UploadHandler:
    """Manages uploaded image files for a single search request."""

    def __init__(self, request_id: Optional[str] = None) -> None:
        self.request_id = request_id or generate_request_id()
        self._upload_dir = Path(settings.UPLOADS_DIR)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._saved_path: Optional[Path] = None

    @property
    def saved_path(self) -> Optional[Path]:
        return self._saved_path

    # ── save helpers ──────────────────────────────────────────────────────────

    async def save_bytes(self, data: bytes, extension: str = ".jpg") -> Path:
        """
        Persist raw image bytes to the uploads directory.
        Called after the Telegram bot downloads a photo.
        """
        ext = extension if extension.startswith(".") else f".{extension}"
        filename = f"{self.request_id}_{timestamp_str()}{ext}"
        dest = self._upload_dir / filename

        # write in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, dest.write_bytes, data)

        logger.info("[%s] Saved upload: %s (%d bytes)", self.request_id, dest, len(data))
        self._saved_path = dest
        return dest

    async def save_from_path(self, source: str | Path) -> Path:
        """Copy an existing file into the managed uploads directory."""
        src = Path(source)
        dest = self._upload_dir / f"{self.request_id}_{src.name}"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, shutil.copy2, str(src), str(dest))
        self._saved_path = dest
        logger.info("[%s] Copied to uploads: %s", self.request_id, dest)
        return dest

    # ── validation ────────────────────────────────────────────────────────────

    def validate(self) -> tuple[bool, str]:
        if not self._saved_path:
            return False, "No file has been saved yet."
        return validate_image_path(self._saved_path)

    # ── cleanup ───────────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Delete the temporary upload file after processing."""
        if self._saved_path and self._saved_path.exists():
            try:
                self._saved_path.unlink()
                logger.debug("[%s] Deleted temp file: %s", self.request_id, self._saved_path)
            except OSError as exc:
                logger.warning("[%s] Could not delete temp file: %s", self.request_id, exc)

    # ── context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "UploadHandler":
        return self

    async def __aexit__(self, *_) -> None:
        self.cleanup()
