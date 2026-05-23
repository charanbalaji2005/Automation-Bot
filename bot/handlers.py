"""
handlers.py — Telegram update handlers.

Each handler is an async function registered with the Application dispatcher.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

from telegram import Message, PhotoSize, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from services.image_service import ImageSearchService
from services.retry_service import RetryService
from utils.helpers import format_results_message
from utils.logger import get_logger

logger = get_logger(__name__)

# Module-level service singletons (shared across handlers)
_search_service = ImageSearchService()
_retry_service  = RetryService()


# ── /start ────────────────────────────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "I can search *PimEyes* for any face in an image.\n\n"
        "📸 Just send me a photo and I'll return the results.\n\n"
        "Commands:\n"
        "/help — show this help\n"
        "/status — check bot status",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /help ─────────────────────────────────────────────────────────────────────

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "*PimEyes Automation Bot — Help*\n\n"
        "1️⃣  Send any photo containing a face.\n"
        "2️⃣  Wait while I search PimEyes (30–60 s).\n"
        "3️⃣  I'll reply with matching result links.\n\n"
        "*Supported formats:* JPG, PNG, WebP\n"
        "*Max size:* 10 MB\n\n"
        "⚠️ Results depend on PimEyes availability.",
        parse_mode=ParseMode.MARKDOWN,
    )


# ── /status ───────────────────────────────────────────────────────────────────

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Bot is online and ready.")


# ── Photo message ─────────────────────────────────────────────────────────────

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message: Message = update.message
    user = update.effective_user

    logger.info("Photo received from user_id=%d", user.id)

    # ── acknowledge immediately ───────────────────────────────────────────────
    status_msg = await message.reply_text(
        "📥 Image received! Starting PimEyes search…\n"
        "_This may take 30–60 seconds._",
        parse_mode=ParseMode.MARKDOWN,
    )

    # ── show typing indicator ─────────────────────────────────────────────────
    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.TYPING,
    )

    try:
        # ── download photo (best quality = last element in list) ──────────────
        photo: PhotoSize = message.photo[-1]
        tg_file = await photo.get_file()

        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        image_bytes = buf.getvalue()

        if not image_bytes:
            await status_msg.edit_text("❌ Could not download your image. Please try again.")
            return

        logger.info(
            "Downloaded photo: file_id=%s size=%d bytes",
            photo.file_id, len(image_bytes)
        )

        # ── run search with retry ─────────────────────────────────────────────
        result = await _retry_service.run(
            _search_service.search_from_bytes,
            image_bytes,
            ".jpg",
            10,   # max_results
        )

        # ── format and send results ───────────────────────────────────────────
        if result["success"] and result["results"]:
            reply = format_results_message(result["results"])
            await status_msg.edit_text(reply, parse_mode=ParseMode.MARKDOWN)

            # Send the first thumbnail as a preview if available
            first_thumb = next(
                (r["thumbnail_url"] for r in result["results"] if r.get("thumbnail_url")),
                None,
            )
            if first_thumb:
                try:
                    await message.reply_photo(
                        photo=first_thumb,
                        caption="🖼 First result preview",
                    )
                except Exception:
                    pass  # thumbnails are best-effort

        elif result["success"] and not result["results"]:
            await status_msg.edit_text(
                "🔍 Search completed but *no results* were found.\n"
                "The face may not be indexed on PimEyes.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            error = result.get("error", "Unknown error")
            await status_msg.edit_text(
                f"❌ Search failed: `{error}`\n\nPlease try again later.",
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as exc:
        logger.exception("Unhandled error in photo_handler: %s", exc)
        await status_msg.edit_text(
            "⚠️ An unexpected error occurred. Please try again.",
        )


# ── Document handler (user sends image as file, not compressed photo) ─────────

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    doc     = message.document

    if not doc or not doc.mime_type or not doc.mime_type.startswith("image/"):
        await message.reply_text("Please send an image file (JPG, PNG, WebP).")
        return

    # Reuse the photo flow by downloading the document
    status_msg = await message.reply_text("📥 Image file received! Processing…")

    try:
        tg_file = await doc.get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        image_bytes = buf.getvalue()

        ext = Path(doc.file_name or "image.jpg").suffix or ".jpg"

        result = await _retry_service.run(
            _search_service.search_from_bytes,
            image_bytes,
            ext,
            10,
        )

        if result["success"] and result["results"]:
            await status_msg.edit_text(
                format_results_message(result["results"]),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            error = result.get("error", "No results found.")
            await status_msg.edit_text(f"❌ {error}")

    except Exception as exc:
        logger.exception("Document handler error: %s", exc)
        await status_msg.edit_text("⚠️ Unexpected error. Please try again.")


# ── Catch-all text ────────────────────────────────────────────────────────────

async def unknown_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "I only understand photos. Send me an image to search PimEyes. 📸"
    )
