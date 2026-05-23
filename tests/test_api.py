"""
test_api.py — Integration tests for the FastAPI endpoints.

Run with:  pytest tests/test_api.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.server import create_app

client = TestClient(create_app())


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_search_no_file():
    resp = client.post("/api/v1/search/image")
    assert resp.status_code == 422   # Unprocessable Entity (missing file)


def test_search_wrong_mime(tmp_path):
    fake_txt = tmp_path / "file.txt"
    fake_txt.write_text("not an image")
    with open(fake_txt, "rb") as f:
        resp = client.post(
            "/api/v1/search/image",
            files={"file": ("file.txt", f, "text/plain")},
        )
    assert resp.status_code == 415
