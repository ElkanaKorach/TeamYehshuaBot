import time
from telegram import Update
from telegram.ext import CallbackContext
from telegram import Bot
from configs.config import TOKEN
from database.db_operations import DatabaseManager
from utils.message_handlers import log_message

bot = Bot(token=TOKEN)
db_cache = DatabaseManager()

async def whitelist_user(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = await message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zur Whitelist hinzufügen möchtest.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    admins = [admin.user.id for admin in await bot.getChatAdministrators(message.chat.id)]

    if message.from_user.id not in admins:
        reply_msg = await message.reply_text("Du hast nicht die Berechtigung, jemanden zur Whitelist hinzuzufügen.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    if not context.args:
        reply_msg = await message.reply_text("Bitte gib an, ob du den Nutzer zur Männer- oder Frauen-Gruppe hinzufügen möchtest: /whitelist sozialmedia , /whitelist frau oder /whitelist mann.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    category = context.args[0].lower()
    mapping = {
        "frau": ("whitelistfemale", "zur Frauen-Whitelist hinzugefügt"),
        "mann": ("whitelistmale", "zur Männer-Whitelist hinzugefügt"),
        "sozialmedia": ("whitelistsozialmedia", "zur SozialMedia-Whitelist hinzugefügt")
    }

    if category not in mapping:
        reply_msg = await message.reply_text("Ungültiges Argument. Benutze /whitelist frau, /whitelist mann oder /whitelist sozialmedia.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    table_name, action_text = mapping[category]
    target_list = db_cache.get_list(table_name)
    target_list.append(user_id)

    db_cache.save_list_to_table(target_list, table_name)

    log_message(message.reply_to_message, action=action_text, reason="Durch Admin-Befehl", deleted=False)

    reply_msg = await message.reply_text(f"Benutzer {user_name} (ID: {user_id}) wurde {action_text}.")
    time.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


async def warn_user(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = await message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du verwarnen möchtest.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    admins = [admin.user.id for admin in await bot.getChatAdministrators(message.chat.id)]

    if message.from_user.id not in admins:
        reply_msg = await message.reply_text("Du hast nicht die Berechtigung, jemanden zu verwarnen.")
        time.sleep(10)
        await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    current_warnings = db_cache.get_warnings(user_id)
    current_warnings += 1
    db_cache.add_warning(user_id, current_warnings, reason="Durch Admin")

    # Logik für das Bannen nach 3 Verwarnungen
    if current_warnings >= 3:
        try:
            await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_id)
            log_message(message.reply_to_message, action="Gebannt",
                        reason=f"Durch Admin-Befehl nach {current_warnings} Verwarnungen", deleted=True)
            reply_msg = await message.reply_text(
                f"Benutzer {user_name} (ID: {user_id}) wurde nach {current_warnings} Verwarnungen gebannt.")
        except Exception as e:
            reply_msg = await message.reply_text(
                f"Fehler beim Bannen des Benutzers {user_name} (ID: {user_id}). Grund: {str(e)}")
    else:
        log_message(message.reply_to_message, action=f"Verwarnt (Warnungen: {current_warnings})",
                    reason="Durch Admin-Befehl", deleted=False)
        reply_msg = await message.reply_text(
            f"Benutzer {user_name} (ID: {user_id}) wurde verwarnt. Anzahl der Warnungen: {current_warnings}")

    time.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
