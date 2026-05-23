"""
logger.py — Centralised logging setup.

Creates two handlers:
  1. RotatingFileHandler → logs/app.log  (all levels)
  2. RotatingFileHandler → logs/errors.log (ERROR+)
  3. StreamHandler       → stdout (DEBUG in dev, INFO in prod)

Usage:
    from utils.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.constants import (
    LOGS_DIR,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
)

# ── ensure log directory exists ──────────────────────────────────────────────
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

_LOG_FILE     = Path(LOGS_DIR) / "app.log"
_ERROR_FILE   = Path(LOGS_DIR) / "errors.log"
_MAX_BYTES    = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3

_formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def _build_root_logger() -> logging.Logger:
    root = logging.getLogger("pimeyes_bot")
    root.setLevel(logging.DEBUG)

    if root.handlers:
        # Already configured — prevent duplicate handlers on re-import
        return root

    # ── all-levels rotating file ─────────────────────────────────────────────
    app_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(_formatter)

    # ── errors-only rotating file ────────────────────────────────────────────
    err_handler = RotatingFileHandler(
        _ERROR_FILE, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(_formatter)

    # ── stdout ───────────────────────────────────────────────────────────────
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(_formatter)

    root.addHandler(app_handler)
    root.addHandler(err_handler)
    root.addHandler(stream_handler)

    return root


_root_logger = _build_root_logger()


def get_logger(name: str) -> logging.Logger:
    """Return a child logger namespaced under the root 'pimeyes_bot' logger."""
    return _root_logger.getChild(name)
