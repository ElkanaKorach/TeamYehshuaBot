import time
from telegram import Update
from telegram.ext import CallbackContext
from utils.warning_handler import bot
from database.db_operations import DatabaseManager

# Assuming the log_message function is located in a module named logger.py
import logging
import utils.logging_c.logging_utils as logging_utils
from utils.logging_c.logging_utils import CustomFilter
# Erstelle einen Filter und füge ihn dem root Logger hinzu
logging_utils.setlogger(logging)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Logging
logger = logging.getLogger(__name__)
filter = CustomFilter(logging)
logger.getLogger().addFilter(filter)

db_cache = DatabaseManager()

def add_to_supporter(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zum Unterstützer hinzufügen möchtest.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]
    if message.from_user.id not in admins:
        reply_msg = update.message.reply_text("Du hast nicht die Berechtigung, jemanden zum Unterstützer hinzuzufügen.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    supporters = db_cache.get_list("supporter")
    supporters.append(user_id)

    # Save the updated supporters list
    db_cache.save_list_to_table(supporters, "supporter")

    reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde als Unterstützer hinzugefügt."
    logger.info(f"User {message.reply_to_message.from_user.first_name} (ID: {message.reply_to_message.from_user.id}) als Unterstützer hinzugefügt. Grund: Durch Admin-Befehl.")


    sent_reply = update.message.reply_text(reply_msg)
    time.sleep(10)
    bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
