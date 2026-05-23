"""
proxy_service.py — Optional proxy rotation to avoid IP bans.

Configure a list of proxies in .env as a JSON array:
  PROXY_LIST='["http://user:pass@proxy1:8080", "http://user:pass@proxy2:8080"]'

[HTK] Set one proxy to http://127.0.0.1:8080 (HTTP Toolkit default)
to intercept all browser traffic during development / reverse engineering.
"""

from __future__ import annotations

import itertools
import json
import os
from typing import Iterator, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class ProxyService:
    """Round-robin proxy selector."""

    def __init__(self) -> None:
        raw = os.getenv("PROXY_LIST", "[]")
        try:
            proxies = json.loads(raw)
        except json.JSONDecodeError:
            proxies = []

        self._proxies: list[str] = proxies
        self._cycle: Iterator[str] = itertools.cycle(proxies) if proxies else iter([])
        logger.info("ProxyService initialised with %d proxy/proxies.", len(proxies))

    def get_next(self) -> Optional[str]:
        """Return next proxy URL or None if no proxies configured."""
        if not self._proxies:
            return None
        return next(self._cycle)

    def build_playwright_proxy(self, proxy_url: Optional[str] = None) -> Optional[dict]:
        """Convert a proxy URL string into Playwright's proxy dict."""
        url = proxy_url or self.get_next()
        if not url:
            return None
        # e.g. http://user:pass@host:port
        from urllib.parse import urlparse
        p = urlparse(url)
        cfg: dict = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
        if p.username:
            cfg["username"] = p.username
        if p.password:
            cfg["password"] = p.password
        return cfg
