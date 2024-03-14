import time
from telegram.ext import CallbackContext
from telegram import Update, Bot
from configs.config import TOKEN
import logging
import utils.logging_c.logging_utils as logging_utils
from utils.logging_c.logging_utils import CustomFilter
from database.db_operations import DatabaseManager
from utils.message_handlers import ADMIN_IDS

# Erstelle einen Filter und füge ihn dem root Logger hinzu
filter = CustomFilter(logging)
logging.getLogger().addFilter(filter)
logging_utils.setlogger(logging)
logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

bot = Bot(token=TOKEN)
db_manager = DatabaseManager()

async def log_and_reply(update, reply_text, admin_only=True):
    message = update.message
    admins = ADMIN_IDS
    if admin_only and message.from_user.id not in admins:
        return
    sent_reply = await message.reply_text(reply_text)
    time.sleep(10)
    await bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

async def update_whitelist(update, context, list_type):
    message = update.message
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if message.from_user.id not in ADMIN_IDS or not user_id:
        return
    current_list = db_manager.get_list(list_type)
    current_list.append(user_id)
    db_manager.save_list_to_table(list_type, current_list)
    reply_msg = f"Benutzer {user_id} wurde zur {list_type} hinzugefügt."
    await log_and_reply(update, reply_msg)

async def show_whitelist(update: Update, context: CallbackContext):
    message = update.message  # Nachricht vom Benutzer
    admins = ADMIN_IDS  # IDs der Admins

    # Prüfung, ob der Befehl von einem Admin kommt
    if message.from_user.id not in admins:
        reply_msg = await update.message.reply_text("Du hast nicht die Berechtigung, die Whitelist anzuzeigen.")
        await log_and_reply(update, reply_msg, admin_only=True)
        return

    # Whitelist-Daten abrufen und in einem Dictionary speichern
    whitelist_data = {
        name: ', '.join(map(str, db_manager.get_list(name)))
        for name in ["whitelistsozialmedia", "whitelistmale", "whitelistfemale", "whitelistparascha"]
    }

    # Antworttext generieren
    reply_text = '\n'.join([f"{key}: {value}" for key, value in whitelist_data.items()])

    # Antwort senden
    await update.message.reply_text(reply_text)
    await log_and_reply(update, "Whitelist wurde angezeigt.", admin_only=True)


async def clear_whitelists(update):
    if update.message.from_user.id not in ADMIN_IDS:
        return
    for list_name in ["whitelistsozialmedia", "whitelistmale", "whitelistfemale", "whitelistparascha"]:
        db_manager.clear_list_table(list_name)
    log_and_reply(update, "Alle Whitelists wurden erfolgreich geleert.")
async def log_message(message, action, reason, deleted):
    log_entry = f"{message.from_user.first_name} (ID: {message.from_user.id}): Aktion: {action}, Grund: {reason}, Gelöscht: {deleted}"
    logging.info(log_entry)

# Zum Whitelist für soziale Medien hinzufügen
async def add_to_whitelistsozialmedia(update: Update, context: CallbackContext):
    message = update.message
    if not message.reply_to_message:
        reply_msg = await message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zur Whitelist für soziale Medien hinzufügen möchtest.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    admins = ADMIN_IDS
    if message.from_user.id not in admins:
        reply_msg = await update.message.reply_text("Du hast nicht die Berechtigung, jemanden zur Whitelist hinzuzufügen.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    whitelistsozialmedia = db_manager.get_list("whitelistsozialmedia")
    whitelistsozialmedia.append(user_id)
    db_manager.whitelistsozialmedia = whitelistsozialmedia
    db_manager.save_list_to_table("whitelistsozialmedia", whitelistsozialmedia)

    reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde zur Whitelist für soziale Medien hinzugefügt."
    log_message(message.reply_to_message, action="zur Whitelist für soziale Medien hinzugefügt", reason="Durch Admin-Befehl", deleted=False)

    sent_reply = await update.message.reply_text(reply_msg)
    time.sleep(10)
    bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

# Der Code wurde hier gekürzt. Im Folgenden sehen Sie die Implementierung für die remove_from_whitelist-Funktion.
async def whitelist_user(update: Update, context: CallbackContext):
    message = update.message  # Nachricht vom Benutzer
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None  # ID des angesprochenen Benutzers
    user_name = message.reply_to_message.from_user.first_name if message.reply_to_message else None  # Name des angesprochenen Benutzers
    admins = ADMIN_IDS  # IDs der Admins

    # Prüfung, ob der Befehl von einem Admin kommt
    if message.from_user.id not in admins:
        reply_msg = await update.message.reply_text("Du hast nicht die Berechtigung, jemanden zur Whitelist hinzuzufügen.")
        return

    # Prüfung, ob eine Nachricht zum Antworten vorhanden ist
    if not user_id:
        reply_msg = await update.message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zur Whitelist hinzufügen möchtest.")
        return

    # Prüfung, welche Whitelist (Männer, Frauen, SozialMedia, etc.)
    list_type = context.args[0].lower() if context.args else None

    # Auswahl der Datenbanktabelle und Liste basierend auf dem Argument
    table_name, action_text = None, ""
    if list_type == "frau":
        table_name, action_text = "whitelistfemale", "zur Frauen-Whitelist hinzugefügt"
    elif list_type == "mann":
        table_name, action_text = "whitelistmale", "zur Männer-Whitelist hinzugefügt"
    elif list_type == "sozialmedia":
        table_name, action_text = "whitelistsozialmedia", "zur SozialMedia-Whitelist hinzugefügt"
    elif list_type == "show":
        await show_whitelist(update, context)
    if not table_name:
        reply_msg = await update.message.reply_text("Ungültiges Argument. Benutze /whitelist frau, /whitelist mann oder /whitelist sozialmedia.")
        return

    # Hinzufügen zur Whitelist und Datenbankaktualisierung
    current_list = db_manager.get_list(table_name)
    current_list.append(user_id)
    db_manager.save_list_to_table(table_name, current_list)

    reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde {action_text}."
    await update.message.reply_text(reply_msg)


async def log_and_delete(msg, text):
    sent_reply = msg.reply_text(text)
    time.sleep(10)
    bot.delete_message(chat_id=msg.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)


async def remove_from_whitelist(update: Update, context: CallbackContext):
    message, args = update.message, context.args

    if not message.reply_to_message:
        log_and_delete(message,
                       "Bitte antworte auf die Nachricht des Nutzers, den du von der Whitelist entfernen möchtest.")
        return

    user_id = message.reply_to_message.from_user.id
    admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]

    if message.from_user.id not in admins:
        log_and_delete(message, "Du hast nicht die Berechtigung, jemanden von der Whitelist zu entfernen.")
        return

    if not args:
        log_and_delete(message, "Bitte gib an, ob du den Nutzer von der Männer- oder Frauen-Gruppe entfernen möchtest.")
        return

    gender = args[0].lower()
    table_map = {
        "frau": "whitelistfemale",
        "mann": "whitelistmale",
        "sozialmedia": "whitelistsozialmedia"
    }
    table_name = table_map.get(gender)

    if not table_name:
        log_and_delete(message, "Ungültiges Argument. Benutze /remove_from_whitelist frau, mann oder sozialmedia.")
        return

    target_list = db_manager.get_list(table_name)
    if user_id not in target_list:
        log_and_delete(message, f"Benutzer ID: {user_id} ist nicht in der Whitelist.")
        return

    target_list.remove(user_id)
    db_manager.save_list_to_table(table_name, target_list)

    action_text = f"Benutzer ID: {user_id} wurde von der {gender}-Whitelist entfernt."
    log_and_delete(message, action_text)
