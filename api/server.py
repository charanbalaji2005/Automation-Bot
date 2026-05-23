"""
server.py — FastAPI application factory.

The REST API lets external services (CI pipelines, web dashboards, etc.)
trigger searches without going through Telegram.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from utils.config import settings
from utils.constants import API_PREFIX
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    logger.info("FastAPI server starting up…")
    yield
    logger.info("FastAPI server shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="PimEyes Automation API",
        description=(
            "REST interface for the PimEyes browser-automation bot. "
            "Upload an image and receive reverse face-search results."
        ),
        version="1.0.0",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        lifespan=_lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # tighten for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── routers ───────────────────────────────────────────────────────────────
    app.include_router(router, prefix=API_PREFIX)

    # ── global exception handler ──────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def _global_exc(request, exc):
        logger.exception("Unhandled API error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )

    return app
