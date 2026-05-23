"""
test_automation.py — Tests for automation helpers.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from utils.validators import validate_image_path, validate_url, sanitize_filename
from utils.helpers import hash_file, truncate


# ── validators ────────────────────────────────────────────────────────────────

def test_validate_image_path_missing():
    ok, reason = validate_image_path("/tmp/does_not_exist.jpg")
    assert not ok
    assert "not found" in reason.lower()


def test_validate_url_valid():
    assert validate_url("https://pimeyes.com/en") is True


def test_validate_url_invalid():
    assert validate_url("not-a-url") is False


def test_sanitize_filename_strips_traversal():
    result = sanitize_filename("../../etc/passwd")
    assert "/" not in result
    assert "." not in result or result.count(".") <= 1


# ── helpers ───────────────────────────────────────────────────────────────────

def test_truncate_short():
    assert truncate("hello", 100) == "hello"


def test_truncate_long():
    s = "x" * 300
    result = truncate(s, 200)
    assert len(result) <= 200
    assert result.endswith("…")
