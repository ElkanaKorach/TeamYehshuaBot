import asyncio
from telegram import Update
from telegram.ext import CallbackContext
import time
import logging
import utils.logging_c.logging_utils as logging_utils
from utils.logging_c.logging_utils import CustomFilter
from configs.config import GENERAL_CHAT_MESSAGE_ID, SOZIALMEDIA_CHAT_MESSAGE_ID, MALE_CHAT_MESSAGE_ID, FEMALE_CHAT_MESSAGE_ID, INFO_CHAT_MESSAGE_ID, TOKEN
from database.db_operations import DatabaseManager


# Erstelle einen Filter und füge ihn dem root Logger hinzu
logging_utils.setlogger(logging)

# Logging
logger = logging.getLogger(__name__)

filter = CustomFilter(logging)
logger.getLogger().addFilter(filter)

db_manager = DatabaseManager()



# Liste der Admin-IDs
ADMIN_IDS = [1082436365, 1438346474]

# Funktion, um zu überprüfen, ob eine Nachricht von einem Admin stammt
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def delete_and_log_message(update, context, reply_text, reason, topic_id=None):
    message = update.message
    try:
        reply_message = await message.reply_text(
            text=reply_text,
            reply_to_message_id=message.message_id
        )
        log_message(message, action="gelöscht (Nutzer informiert)", reason=reason, deleted=True, topic_id=topic_id)
        await asyncio.sleep(10)
        await context.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        await context.bot.delete_message(chat_id=message.chat.id, message_id=reply_message.message_id)
    except Exception as e:
        logger.warning(f"Couldn't delete message due to: {e}")
        log_message(message, action="nicht gelöscht", reason="Fehler beim Löschen", deleted=False, topic_id=topic_id)

def log_message(message, action, reason, deleted, topic_id=None):
    log_entry = f"{message.from_user.first_name} (ID: {message.from_user.id}): " \
                f"Action: {action}, Reason: {reason}, Deleted: {deleted}"

    if topic_id:
        log_entry += f", Topic ID: {topic_id}"
    log_entry += "\n"

    with open('log.txt', 'a') as log_file:
        log_file.write(log_entry)
    logger.info(log_entry)

async def delete_general_messages(update: Update, context: CallbackContext):
    message = update.message

    if message.from_user.is_bot:
        return

    temp = message.chat_id
    forum_info = message.reply_to_message
    try:
        i = update.message.reply_to_message.forum_topic_created.name
    except:
        i = None

    if is_admin(message.from_user.id):
        log_message(message, action="nicht gelöscht (Admin)", reason="Nachricht von Admin", deleted=False, topic_id=i)
        return

    if i is None:
        reply_text = "Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Halte dich an die Themenregeln der Gruppe."
        await delete_and_log_message(update, context, reply_text, "Nachricht ohne ID", topic_id=i)
        return

    if i == GENERAL_CHAT_MESSAGE_ID or message.from_user.id in db_manager.get_list("whitelistparascha"):
        log_message(message, action="nicht gelöscht", reason="Allgemeines Thema oder in Whitelist Parascha",
                    deleted=False, topic_id=i)
    elif i == SOZIALMEDIA_CHAT_MESSAGE_ID:
        if message.from_user.id not in db_manager.get_list("whitelistsozialmedia"):
            reply_text = "Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Halte dich an die Themenregeln der Gruppe."
            await delete_and_log_message(update, context, reply_text, "Nachricht von Nicht-Whitelist", topic_id=i)
    elif i == MALE_CHAT_MESSAGE_ID:
        if message.from_user.id not in db_manager.get_list("whitelistmale"):
            reply_text = "Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Du wurdest entweder noch nicht Hinzugefügt oder bist kein Mann. Bitte schreibe bis dahin im Allgemeinen Chat. Und Bitte dort um Freischaltung."
            await delete_and_log_message(update, context, reply_text, "Nachricht von Nicht-Whitelist Männer", topic_id=i)
    elif i == FEMALE_CHAT_MESSAGE_ID:
        if message.from_user.id not in db_manager.get_list("whitelistfemale"):
            reply_text = "Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Du wurdest entweder noch nicht Hinzugefügt oder bist keine Frau. Bitte schreibe bis dahin im Allgemeinen Chat. Und Bitte dort um Freischaltung."
            await delete_and_log_message(update, context, reply_text, "Nachricht von Nicht-Whitelist Frauen", topic_id=i)
    elif i == INFO_CHAT_MESSAGE_ID:
        if message.from_user.id not in db_manager.get_list("whitelistinfo"):
            reply_text = "Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Halte dich an die Themenregeln der Gruppe."
            await delete_and_log_message(update, context, reply_text, "Nachricht von Nicht-Whitelist", topic_id=i)
    else:
        log_message(message, action="nicht gelöscht", reason="Andere Themen-ID", deleted=False, topic_id=i)
