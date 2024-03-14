import os
import time

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from configs.config import TOKEN
from utils.whitelist_handler import whitelist_user as utils_whitelist_user
from utils.message_handlers import delete_general_messages
from utils.whitelist_handler import remove_from_whitelist
from utils.supporter_handler import add_to_supporter
from utils.warning_handler import warn_user
from utils.ban_handler import ban_user
from utils.user_data import load_warned_users
<<<<<<< HEAD
=======
import logging_c.logging_utils
import logging
>>>>>>> 82bf4e0d2916f330878511e40c0d2a3c68c8dba4

# Erstelle einen Filter und füge ihn dem root Logger hinzu
logging_c.logging_utils.setlogger(logging)

# Muted Users Dictionary
muted_users = {}
<<<<<<< HEAD

import logging
from datetime import datetime


class CustomFilter(logging.Filter):
    def filter(self, record):
        # Überprüfe, ob die Nachricht einen bestimmten Text enthält
        if 'HTTP Request: POST https://api.telegram.org/bot6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak' in record.getMessage():
            return False  # Filtere diese Nachrichten aus
        return True  # Zeichne alle anderen Nachrichten auf


# Konfiguriere das grundlegende Logging-Setup
current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
log_filename = f'log/log_{current_time}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Erstelle einen Filter und füge ihn dem root Logger hinzu
filter = CustomFilter()
logging.getLogger().addFilter(filter)

=======
>>>>>>> 82bf4e0d2916f330878511e40c0d2a3c68c8dba4

# Whitelist-Funktion
async def whitelist_user(update: Update, context: CallbackContext):
    try:
        await utils_whitelist_user(update, context)
    except BadRequest as e:
        if str(e) == "Replied message not found":
            await update.message.reply_text("Ungültiges Argument. Die Antwortnachricht wurde nicht gefunden.")
        else:
            await update.message.reply_text(f"Ein Fehler ist aufgetreten: {e}")


# Entferne Nutzer aus Whitelist
async def handle_remove_from_whitelist(update, context):
    await remove_from_whitelist(update, context)


# Füge Nutzer zu Supportern hinzu
async def handle_add_to_supporter(update, context):
    await add_to_supporter(update, context)


# Verwarne Nutzer
async def handle_warn(update, context):
    await warn_user(update, context)


# Banne Nutzer
async def handle_ban(update, context):
    await ban_user(update, context)


# Allgemeine Nachrichten und Spam-Handling
async def handle_text_and_spam(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in muted_users and time.time() < muted_users[user_id]:
        try:
            await update.message.delete()
        except Exception as e:
            logging.error(f"Fehler beim Löschen der Nachricht: {e}")
    else:
        await delete_general_messages(update, context)


async def handle_mute(update: Update, context: CallbackContext):
    # Mutet einen Benutzer für eine bestimmte Zeit
    try:
        user_to_mute = update.message.reply_to_message.from_user.id
        mute_time = int(context.args[0])
        muted_users[user_to_mute] = time.time() + mute_time
        await update.message.reply_text(f"Benutzer {user_to_mute} für {mute_time} Sekunden stummgeschaltet.")
    except Exception as e:
        await update.message.reply_text(f"Ein Fehler ist aufgetreten: {e}")


# Hauptfunktion
def main():
    # Erstellen des Updater und passen des Dispatchers
    dp = ApplicationBuilder().token(TOKEN).build()

    # Hinzufügen der Handler
    dp.add_handler(CommandHandler('whitelist', whitelist_user))
    dp.add_handler(CommandHandler('removefromwhitelist', handle_remove_from_whitelist))
    dp.add_handler(CommandHandler('addsupporter', handle_add_to_supporter))
    dp.add_handler(CommandHandler('warn', handle_warn))
    dp.add_handler(CommandHandler('ban', handle_ban))
    dp.add_handler(CommandHandler('mute', handle_mute))

    # Dies sollte der letzte Handler sein
    dp.add_handler(MessageHandler(filters.ALL, handle_text_and_spam))

    # Bot starten
    dp.run_polling()


# Ausführen des Hauptprogramms
if __name__ == '__main__':
    load_warned_users()  # Lade zuvor gewarnte Nutzer
    main()
