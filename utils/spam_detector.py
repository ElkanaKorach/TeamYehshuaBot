import time
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.storage import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from configs.config import TOKEN
from utils.admin_check import is_admin  # Stellen Sie sicher, dass is_admin mit aiogram kompatibel ist

user_message_count = {}
user_warnings = {}

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)


async def check_spam(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if await is_admin(message, bot):
        return

    if user_id not in user_message_count:
        user_message_count[user_id] = 0
    user_message_count[user_id] += 1

    if user_message_count[user_id] > 10:
        if user_id not in user_warnings:
            user_warnings[user_id] = 0
        user_warnings[user_id] += 1

        if user_warnings[user_id] == 1:
            reply_message = await message.reply("Bitte sende nicht mehr als 10 Nachrichten pro Minute.")
        else:
            reply_message = await message.reply("Spam erkannt vom System! Dies ist eine Verwarnung.")

        time.sleep(10)
        await bot.delete_message(chat_id=chat_id, message_id=reply_message.message_id)
        user_message_count[user_id] = 0


@dp.message_handler()
async def handle_message(message: types.Message, state: FSMContext):
    await check_spam(message)

