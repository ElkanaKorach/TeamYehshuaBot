from telegram.ext import Updater, MessageHandler, Filters
import logging

# Ersetze 'YOUR_TOKEN_HERE' mit dem Token deines Bots
TOKEN = '6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak'

# Logging-Konfiguration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Handler-Funktion, die bei jeder neuen Nachricht aufgerufen wird
def echo(update, context):
    logger.info(f"Nachricht von {update.message.from_user.name}: {update.message.text}")

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
