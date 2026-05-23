"""
telegram_bot.py — Build and return the configured Telegram Application.

Supports both polling (default) and webhook modes.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.commands import register_commands
from bot.handlers import (
    document_handler,
    help_handler,
    photo_handler,
    start_handler,
    status_handler,
    unknown_handler,
)
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def build_application() -> Application:
    """Construct the Application with all handlers registered."""
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ── Command handlers ──────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  start_handler))
    app.add_handler(CommandHandler("help",   help_handler))
    app.add_handler(CommandHandler("status", status_handler))

    # ── Media handlers ────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.IMAGE, document_handler))

    # ── Fallback ──────────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_handler))

    logger.info("Telegram Application built with all handlers.")
    return app


async def start_polling(app: Application) -> None:
    """Run bot in long-polling mode (for local / dev use)."""
    logger.info("Starting bot in POLLING mode…")
    await register_commands(app)
    await app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


async def start_webhook(app: Application, webhook_url: str, port: int = 8443) -> None:
    """Run bot in webhook mode (for production / server deployments)."""
    logger.info("Starting bot in WEBHOOK mode: %s", webhook_url)
    await register_commands(app)
    await app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=webhook_url,
    )
