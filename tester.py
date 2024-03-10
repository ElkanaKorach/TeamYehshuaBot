import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from configs.config import TOKEN

# Logging-Einstellungen
logging.basicConfig(level=logging.DEBUG)

API_TOKEN = TOKEN

storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(lambda message: message.chat.type in ['group', 'supergroup'])
async def handle_group_message(message: types.Message):
    topic_info = "Kein Thema"

    reply = message.reply_to_message
    if reply:
        forum_info = reply.values.get("forum_topic_created").get("name")
        if forum_info:
            # Extrahieren des Thema-Namens und der Icon-Farbe aus forum_info
            topic_name = getattr(forum_info, 'name', 'Unbekannt')
            icon_color = getattr(forum_info, 'icon_color', 'Unbekannt')

            # Ausgabe der Informationen
            print(f"Thema-Name: {topic_name}, Icon-Farbe: {icon_color}")
        else:
            # Ausgabe, wenn kein spezifisches Thema gefunden wurde
            print("Kein spezifisches Thema gefunden.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
