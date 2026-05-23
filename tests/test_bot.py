"""
test_bot.py — Unit tests for Telegram bot handlers.

Run with:  pytest tests/test_bot.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from utils.helpers import format_results_message


# ── format_results_message ────────────────────────────────────────────────────

def test_format_results_empty():
    msg = format_results_message([])
    assert "No results" in msg


def test_format_results_with_data():
    results = [
        {"url": "https://example.com/page1", "title": "Example Page", "thumbnail_url": ""},
        {"url": "https://example.com/page2", "title": "Another Page", "thumbnail_url": ""},
    ]
    msg = format_results_message(results)
    assert "2 result" in msg
    assert "Example Page" in msg
    assert "https://example.com/page1" in msg


def test_format_results_long_title():
    results = [{"url": "https://x.com", "title": "A" * 300, "thumbnail_url": ""}]
    msg = format_results_message(results)
    # Title should be truncated
    assert len(msg) < 1000
