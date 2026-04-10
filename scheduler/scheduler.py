"""
Message Scheduler
Runs inside the bot's JobQueue every 60 seconds.
Checks scheduled_messages table and sends due messages.
"""

import json
import logging
import os

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.db_operations import DatabaseManager

logger = logging.getLogger(__name__)
db = DatabaseManager()


# ─────────────────────────────────────────────
#  Button builder
# ─────────────────────────────────────────────

def _build_keyboard(buttons_json: str):
    """Parse stored JSON and return InlineKeyboardMarkup or None."""
    if not buttons_json:
        return None
    try:
        rows_data = json.loads(buttons_json)
        keyboard = []
        for row in rows_data:
            kb_row = []
            for btn in row:
                text = btn.get("text", "Button")
                if btn.get("url"):
                    kb_row.append(InlineKeyboardButton(text, url=btn["url"]))
                elif btn.get("callback_data"):
                    kb_row.append(InlineKeyboardButton(text, callback_data=btn["callback_data"]))
            if kb_row:
                keyboard.append(kb_row)
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    except Exception as e:
        logger.error(f"Button parse error: {e}")
        return None


# ─────────────────────────────────────────────
#  Media resolver
# ─────────────────────────────────────────────

def _get_media(msg: dict):
    """Return the best available media source: file_id > url > local file."""
    if msg.get("media_file_id"):
        return msg["media_file_id"]
    if msg.get("media_url"):
        return msg["media_url"]
    path = msg.get("media_local_path")
    if path and os.path.exists(path):
        return open(path, "rb")
    return None


# ─────────────────────────────────────────────
#  Single message sender
# ─────────────────────────────────────────────

async def send_scheduled_message(bot: Bot, msg: dict):
    """Send one scheduled message via the Telegram Bot API."""
    chat_id      = msg["chat_id"]
    msg_type     = msg["message_type"]
    content      = msg.get("content") or ""
    caption      = msg.get("caption") or ""
    reply_markup = _build_keyboard(msg.get("buttons_json"))

    if msg_type == "text":
        await bot.send_message(
            chat_id=chat_id,
            text=content,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    elif msg_type == "photo":
        media = _get_media(msg)
        if not media:
            raise ValueError("Kein Bild angegeben")
        await bot.send_photo(
            chat_id=chat_id,
            photo=media,
            caption=caption or None,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    elif msg_type == "video":
        media = _get_media(msg)
        if not media:
            raise ValueError("Kein Video angegeben")
        await bot.send_video(
            chat_id=chat_id,
            video=media,
            caption=caption or None,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    elif msg_type == "document":
        media = _get_media(msg)
        if not media:
            raise ValueError("Keine Datei angegeben")
        await bot.send_document(
            chat_id=chat_id,
            document=media,
            caption=caption or None,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    elif msg_type == "audio":
        media = _get_media(msg)
        if not media:
            raise ValueError("Keine Audiodatei angegeben")
        await bot.send_audio(
            chat_id=chat_id,
            audio=media,
            caption=caption or None,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )

    else:
        raise ValueError(f"Unbekannter Nachrichtentyp: {msg_type}")


# ─────────────────────────────────────────────
#  JobQueue callback (every 60 s)
# ─────────────────────────────────────────────

async def check_and_send_scheduled(context: ContextTypes.DEFAULT_TYPE):
    """Called by bot JobQueue every minute."""
    due = db.get_due_scheduled_messages()
    if not due:
        return
    logger.info(f"Scheduler: {len(due)} fällige Nachricht(en) gefunden")
    for msg in due:
        try:
            await send_scheduled_message(context.bot, msg)
            db.mark_message_sent(msg["id"])
            logger.info(f"Nachricht #{msg['id']} gesendet")
        except Exception as e:
            logger.error(f"Nachricht #{msg['id']} fehlgeschlagen: {e}")
            db.mark_message_failed(msg["id"], str(e))
