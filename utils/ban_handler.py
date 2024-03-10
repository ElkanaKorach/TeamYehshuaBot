import time
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext
import logging

logger = logging.getLogger(__name__)

async def extract_user_id(update: Update, context: CallbackContext) -> int:
    """Extracts and returns the user ID from a replied-to message or the command's arguments."""

    # Wenn auf eine Nachricht geantwortet wurde
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id

    # Falls eine Benutzer-ID als Argument gegeben wurde
    elif context.args:
        try:
            return int(context.args[0])  # versucht das erste Argument in eine Zahl (user_id) zu konvertieren
        except ValueError:
            return None  # Wenn das erste Argument keine Zahl ist

    # Falls keine ID gefunden wurde
    return None


async def ban_user(update: Update, context: CallbackContext):
    user_id = await extract_user_id(update, context)
    bot = context.bot
    chat_id = update.message.chat_id
    sender_id = update.message.from_user.id
    response_msg = None

    # Überprüfe, ob der Sender ein Admin ist
    admins = [admin.user.id for admin in await bot.get_chat_administrators(chat_id)]
    if sender_id not in admins:
        response_msg = await update.message.reply_text("Du hast nicht die Berechtigung, Benutzer zu bannen.")
    else:
        if not user_id:
            response_msg = await update.message.reply_text(
                "Du musst auf eine Nachricht eines Benutzers antworten oder seine Benutzer-ID angeben.")
        else:
            reason = ' '.join(context.args[1:]) if context.args else None
            try:
                await bot.banChatMember(chat_id, user_id)
                response_msg = await update.message.reply_text(
                    f"Benutzer wurde gebannt! Grund: {reason if reason else 'Kein Grund angegeben.'}")
            except BadRequest as e:
                response_msg = await update.message.reply_text(f"Fehler: {e.message}")
                logger.error(f"BadRequest: {e.message}")
            except Exception as e:
                logger.warning(f"Couldn't ban user due to: {e}")
                response_msg = await update.message.reply_text(f"Fehler: {e}")

    # Lösche die Befehlsnachricht und die Antwort des Bots nach 10 Sekunden
    time.sleep(10)
    await bot.delete_message(chat_id, update.message.message_id)
    if response_msg:
        await bot.delete_message(chat_id, response_msg.message_id)
