"""
routes.py — API route definitions.

Endpoints:
  GET  /health            — liveness probe
  POST /search/image      — upload image file, get results
  POST /search/url        — provide image URL, get results (not implemented)
"""

from __future__ import annotations

import io
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.image_service import ImageSearchService
from services.retry_service import RetryService
from utils.constants import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

_search_service = ImageSearchService()
_retry_service  = RetryService()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "pimeyes-automation-bot"}


# ── Search by file upload ─────────────────────────────────────────────────────

class SearchResult(BaseModel):
    url:           str
    title:         str
    thumbnail_url: str
    source_domain: str


class SearchResponse(BaseModel):
    success:    bool
    request_id: str
    results:    List[SearchResult]
    error:      Optional[str] = None


@router.post("/search/image", response_model=SearchResponse, tags=["search"])
async def search_by_image(
    file: UploadFile = File(..., description="Image to search (JPG/PNG/WebP, max 10 MB)"),
    max_results: int = 10,
):
    """
    Upload an image and receive PimEyes reverse face-search results.
    """
    # ── validate content-type ─────────────────────────────────────────────────
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {file.content_type}. "
                   f"Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # ── read + size check ─────────────────────────────────────────────────────
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(image_bytes) // 1024} KB). "
                   f"Max: {MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB.",
        )

    logger.info(
        "API search request: filename=%s size=%d content_type=%s",
        file.filename, len(image_bytes), file.content_type
    )

    # ── infer extension ───────────────────────────────────────────────────────
    ext = "." + (file.content_type or "image/jpeg").split("/")[-1]
    ext = ext.replace("/webp", ".webp")

    result = await _retry_service.run(
        _search_service.search_from_bytes,
        image_bytes,
        ext,
        max_results,
    )

    return JSONResponse(content=result, status_code=200 if result["success"] else 500)
