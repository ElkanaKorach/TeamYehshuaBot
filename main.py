from telegram.ext import Updater, MessageHandler, Filters
import logging
from datetime import datetime

# Ersetze 'YOUR_TOKEN_HERE' mit dem Token deines Bots
TOKEN = '6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak'

# Logging-Konfiguration
# shellcheck disable=SC1065
# shellcheck disable=SC1072
# shellcheck disable=SC1073
# shellcheck disable=SC1064
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Handler-Funktion, die bei jeder neuen Nachricht aufgerufen wird
def echo(update, context):
    chat_type = update.message.chat.type
    chat_id = update.message.chat.id
    user_name = update.message.from_user.name
    message_text = update.message.text
    message_date = update.message.date
    reply_to_message = update.message.chat.location

    logger.info(f"Nachricht von {user_name} im {chat_type} (ID: {chat_id}): '{message_text}', Zeit: {message_date}, {reply_to_message}")

def main():
    # Updater und Dispatcher initialisieren
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handler, der auf alle Textnachrichten reagiert
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Startet den Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
