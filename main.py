import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Ersetze '6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak' mit dem Token deines Bots
TOKEN = '6942337491:AAGVKMvHayewt5CUcNFg8xx_zprobgJ4jak'

# Logging-Konfiguration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_type = update.effective_chat.type
    chat_id = update.effective_chat.id
    user_name = update.effective_user.name
    message_text = update.message.text
    message_date = update.message.date
    reply_to_message = update.message.reply_to_message

    logger.info(f"Nachricht von {user_name} im {chat_type} (ID: {chat_id}): '{message_text}', Zeit: {message_date}, Antwort auf Nachricht: {reply_to_message}")

async def main() -> None:
    # Erstelle eine Anwendung und gib dein Bot Token an
    application = Application.builder().token(TOKEN).build()

    # Füge einen MessageHandler hinzu, der auf alle Textnachrichten reagiert
    application.add_handler(MessageHandler(filters.Text and (not filters.Command), echo))

    try:
        # Start the bot
        polling_task = asyncio.create_task(application.run_polling())

        # Wait for the polling task to complete before closing the event loop
        await polling_task

    finally:
        # Close the event loop after finishing
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
