"""
Welcome / Farewell Handler
Manages new-member welcome messages and group leave notifications.
Also stores per-chat rules and welcome message templates in SQLite.
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.db_operations import DatabaseManager

logger = logging.getLogger(__name__)

db = DatabaseManager()


# ─────────────────────────────────────────────
#  New member
# ─────────────────────────────────────────────

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when a new user joins."""
    chat = update.effective_chat
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        template = get_welcome_message(chat.id)
        if template:
            text = template.format(
                name=member.first_name or "User",
                id=member.id,
                chat=chat.title or "dieser Gruppe",
            )
        else:
            text = (
                f"Schalom <b>{member.first_name}</b>! "
                f"Willkommen in <b>{chat.title or 'dieser Gruppe'}</b>.\n\n"
                "Bitte lies die Regeln (/rules) bevor du schreibst."
            )

        try:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"Welcome message failed: {e}")


# ─────────────────────────────────────────────
#  Left member
# ─────────────────────────────────────────────

async def handle_left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a farewell message when a user leaves."""
    member = update.message.left_chat_member
    if member.is_bot:
        return
    try:
        await update.message.reply_text(
            f"Auf Wiedersehen, <b>{member.first_name}</b>!",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.warning(f"Farewell message failed: {e}")


# ─────────────────────────────────────────────
#  Rules helpers
# ─────────────────────────────────────────────

def get_group_rules(chat_id: int) -> str:
    """Return group rules for chat_id or empty string."""
    return db.get_setting(chat_id, "rules") or ""


def set_group_rules(chat_id: int, rules: str):
    """Persist group rules for chat_id."""
    db.set_setting(chat_id, "rules", rules)


# ─────────────────────────────────────────────
#  Welcome message helpers
# ─────────────────────────────────────────────

def get_welcome_message(chat_id: int) -> str:
    """Return welcome message template for chat_id or empty string."""
    return db.get_setting(chat_id, "welcome") or ""


def set_welcome_message(chat_id: int, template: str):
    """Persist welcome message template for chat_id."""
    db.set_setting(chat_id, "welcome", template)
