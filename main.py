"""
main.py — Application entry point.

Starts both the FastAPI server and the Telegram bot concurrently.

Usage:
    python main.py              # bot + API together
    python main.py --bot-only   # only Telegram bot
    python main.py --api-only   # only FastAPI
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import uvicorn

from api.server import create_app
from bot.telegram_bot import build_application, start_polling
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PimEyes Automation Bot")
    p.add_argument("--bot-only", action="store_true", help="Run only the Telegram bot")
    p.add_argument("--api-only", action="store_true", help="Run only the FastAPI server")
    return p.parse_args()


async def run_api() -> None:
    """Run FastAPI via uvicorn programmatically."""
    app = create_app()
    config = uvicorn.Config(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="info" if not settings.DEBUG else "debug",
        reload=False,
    )
    server = uvicorn.Server(config)
    logger.info("API starting on http://%s:%d", settings.API_HOST, settings.API_PORT)
    await server.serve()


async def run_bot() -> None:
    """Run Telegram bot in polling mode."""
    app = build_application()
    await start_polling(app)


async def run_both() -> None:
    """Run API and bot concurrently."""
    await asyncio.gather(
        run_api(),
        run_bot(),
    )


def main() -> None:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("PimEyes Automation Bot starting…")
    logger.info("Headless: %s | Debug: %s", settings.HEADLESS, settings.DEBUG)
    logger.info("=" * 60)

    if args.bot_only:
        asyncio.run(run_bot())
    elif args.api_only:
        asyncio.run(run_api())
    else:
        asyncio.run(run_both())


if __name__ == "__main__":
    main()
