"""
result_extractor.py — Extract structured results from the PimEyes results page.

After PimEyesSearch.search() completes the browser is sitting on the results
page.  This module scrapes every visible result card and returns a list of dicts.

[HTK] Alternative approach: instead of DOM scraping, intercept the XHR call
that populates the results (usually POST /api/v2/search/face or similar).
HTTP Toolkit shows the full JSON response which is far easier to parse.
Reconstruct it with httpx and skip the browser entirely for extraction.
"""

from __future__ import annotations

import asyncio
from typing import List, Optional

from playwright.async_api import Page

from utils.logger import get_logger

logger = get_logger(__name__)

# Result card selector candidates — PimEyes updates its CSS class names regularly.
# Priority order: most specific → most generic.
_CARD_SELECTORS = [
    "[class*='result-item']",
    "[class*='ResultItem']",
    "[class*='result-card']",
    "[class*='ResultCard']",
    ".search-results > div",
    "[data-testid*='result']",
]

_LINK_SELECTORS   = ["a[href^='http']", "a[href]"]
_IMG_SELECTORS    = ["img[src^='http']", "img[src]"]
_TITLE_SELECTORS  = ["h2", "h3", "p", "[class*='title']", "[class*='domain']"]


async def extract_results(page: Page, max_results: int = 20) -> List[dict]:
    """
    Scrape result cards from the current page.

    Returns a list of:
        {
            "url":           str,   # destination page URL
            "title":         str,   # page title or domain
            "thumbnail_url": str,   # preview image src
            "source_domain": str,
        }
    """
    logger.info("Starting result extraction (max=%d)…", max_results)

    # Try each card selector until we find results
    cards_handle = None
    for sel in _CARD_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=5000, state="visible")
            cards_handle = await page.query_selector_all(sel)
            if cards_handle:
                logger.debug("Found %d cards with selector: %s", len(cards_handle), sel)
                break
        except Exception:
            continue

    if not cards_handle:
        # Fallback: extract all external links from page
        logger.warning("No result cards found; falling back to link extraction.")
        return await _extract_links_fallback(page, max_results)

    results: List[dict] = []

    for card in cards_handle[:max_results]:
        entry = await _parse_card(card)
        if entry:
            results.append(entry)

    logger.info("Extracted %d results.", len(results))
    return results


async def _parse_card(card) -> Optional[dict]:
    """Extract fields from a single result card element."""
    try:
        url   = await _find_attr(card, _LINK_SELECTORS, "href")
        thumb = await _find_attr(card, _IMG_SELECTORS, "src")
        title = await _find_text(card, _TITLE_SELECTORS)

        if not url:
            return None

        domain = _domain_from_url(url)
        return {
            "url":           url,
            "title":         title or domain,
            "thumbnail_url": thumb or "",
            "source_domain": domain,
        }
    except Exception as exc:
        logger.warning("Card parse error: %s", exc)
        return None


async def _find_attr(parent, selectors: list[str], attr: str) -> Optional[str]:
    for sel in selectors:
        try:
            el = await parent.query_selector(sel)
            if el:
                val = await el.get_attribute(attr)
                if val:
                    return val
        except Exception:
            continue
    return None


async def _find_text(parent, selectors: list[str]) -> Optional[str]:
    for sel in selectors:
        try:
            el = await parent.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        except Exception:
            continue
    return None


async def _extract_links_fallback(page: Page, max_results: int) -> List[dict]:
    """Last-resort: grab all outbound links from the page."""
    links = await page.evaluate(
        """
        () => Array.from(document.querySelectorAll('a[href^="http"]'))
              .map(a => ({
                  url:   a.href,
                  title: a.textContent.trim() || a.href,
              }))
              .filter(l => !l.url.includes('pimeyes.com'))
        """
    )
    seen: set = set()
    results = []
    for link in links:
        if link["url"] not in seen:
            seen.add(link["url"])
            results.append({
                "url":           link["url"],
                "title":         link["title"] or _domain_from_url(link["url"]),
                "thumbnail_url": "",
                "source_domain": _domain_from_url(link["url"]),
            })
            if len(results) >= max_results:
                break
    return results


def _domain_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return url
