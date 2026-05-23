"""
commands.py — Register bot commands with Telegram's menu.
"""

from __future__ import annotations

from telegram import BotCommand
from telegram.ext import Application

COMMANDS = [
    BotCommand("start",  "Start the bot and see welcome message"),
    BotCommand("help",   "Show usage instructions"),
    BotCommand("status", "Check if the bot is online"),
]


async def register_commands(app: Application) -> None:
    """Set the bot command list visible in Telegram's menu."""
    await app.bot.set_my_commands(COMMANDS)
