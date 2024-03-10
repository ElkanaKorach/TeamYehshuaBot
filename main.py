import os
import asyncio
from telegram import Update, Chat
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from datetime import datetime

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
    application.add_handler(MessageHandler(filters.text & (~filters.command), echo))

    # Starte den Bot
    task = asyncio.create_task(application.run_polling())
    await asyncio.gather(task)

if __name__ == "__main__":
    asyncio.run(main())