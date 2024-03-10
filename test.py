import logging
from telegram import Bot, Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from telegram.ext import CommandHandler
import time
import mysql.connector
from telegram.error import BadRequest
import os
from datetime import datetime



# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = '6352268704:AAETEKHAV3gacrFEKxLPSLxFH2-UHHzFaLw'  # Hier sollte Ihr Bot-Token stehen

bot = Bot(token=TOKEN)


def create_connection():
    connection = mysql.connector.connect(
        host="192.168.178.201",
        user="teamyehshuatelegrambot",
        password="Ng/rfEi_a7ir)28w",
        database="teamyehshuatelegrambot"
    )
    return connection

def load_warned_users_from_db():
    connection = create_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT user_id FROM warnings")
        users = cursor.fetchall()
        return [user[0] for user in users]
    except mysql.connector.Error as e:
        print(f"MySQL error: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

warned_users = []

def load_warned_users():
    global warned_users
    warned_users = load_warned_users_from_db()
    print(f"Geladene {len(warned_users)} verwarnte Nutzer.")


def load_list_from_table(table_name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT userid FROM {table_name}")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return [user[0] for user in users]

# Liste der Benutzer-IDs, die auf der Whitelist stehen
whitelistsozialmedia = load_list_from_table("whitelistsozialmedia")
whitelistfemale = load_list_from_table("whitelistfemale")
whitelistmale = load_list_from_table("whitelistmale")
supporters = load_list_from_table("supporter")
user_warnings = {}



def save_list_to_table(data, table_name):
    conn = create_connection()
    cursor = conn.cursor()

    # Zuerst löschen Sie alle Einträge
    cursor.execute(f"DELETE FROM {table_name}")

    for userid in data:
        cursor.execute(f"INSERT INTO {table_name} (userid) VALUES ({userid})")
    conn.commit()
    cursor.close()
    conn.close()



def log_message(message, action, reason, deleted=False):
    debug_info = {
        "Nutzer": f"{message.from_user.first_name} (ID: {message.from_user.id})",
        "Wo": f"{message.chat.title} (ID: {message.chat.id})",
        "Aktion": action,
        "Begründung": reason,
        "Themen ID": f"Topic ID: {message.reply_to_message.message_id}" if message.reply_to_message else "No topic detected",
        "Nachricht": f"'{message.text}'"
    }
    logger.info(" - ".join([f"{key}: {value}" for key, value in debug_info.items()]))

def delete_general_messages(update: Update, context: CallbackContext):
    message = update.message
    if not message.from_user.is_bot and message.text and message.text.lower() != "/start":
        try:
            i = message.reply_to_message.message_id
        except:
            i = None

        admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]

        if (message.from_user.id not in admins):
            if i is None or i == 272:
                if message.from_user.id in admins:
                    log_message(message, action="nicht gelöscht (Admin)", reason="Nachricht von Admin", deleted=False)
                else:
                    try:
                        # Send information that this is not a general chat
                        reply_message = message.reply_text(
                            text="Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Halte dich an die Themenregeln der Gruppe.",
                            reply_to_message_id=message.message_id
                        )
                        log_message(message, action="gelöscht (Nutzer informiert)", reason="Nachricht ohne ID", deleted=True)

                        # Delete the sender's message after 10 seconds
                        time.sleep(10)
                        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                        # Delete the bot's message after 10 seconds
                        bot.delete_message(chat_id=message.chat.id, message_id=reply_message.message_id)
                    except Exception as e:
                        logger.warning(f"Couldn't delete message due to: {e}")
                        log_message(message, action="nicht gelöscht", reason="Fehler beim Löschen", deleted=False)
                        pass
            elif i == 2:
                if message.from_user.id in whitelistsozialmedia or message.from_user.id in admins:
                    log_message(message, action="nicht gelöscht (Whitelist/Admin)", reason="Nachricht von Whitelist oder Admin", deleted=False)
                else:
                    try:
                        # Send information as a reply to the message
                        reply_message = message.reply_text(
                            text="Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Halte dich an die Themenregeln der Gruppe.",
                            reply_to_message_id=message.message_id
                        )
                        log_message(message, action="gelöscht (Nutzer informiert)", reason="Nachricht von Nicht-Whitelist", deleted=True)

                        # Delete the sender's message after 10 seconds
                        time.sleep(10)
                        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                        # Delete the bot's message after 10 seconds
                        bot.delete_message(chat_id=message.chat.id, message_id=reply_message.message_id)
                    except Exception as e:
                        logger.warning(f"Couldn't delete message due to: {e}")
                        log_message(message, action="nicht gelöscht", reason="Fehler beim Löschen", deleted=False)
                        pass
            elif i == 271:
                if message.from_user.id in whitelistmale or message.from_user.id in admins:
                    log_message(message, action="nicht gelöscht (Whitelist/Admin)", reason="Nachricht von Whitelist oder Admin", deleted=False)
                else:
                    try:
                        # Send information as a reply to the message
                        reply_message = message.reply_text(
                            text="Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Du wurdest entweder noch nicht Hinzugefügt oder bist keine Mann. Bitte schreibe bis dahin im Allgemeinen Chat. Und Bitte dort um Freischaltung.",
                            reply_to_message_id=message.message_id
                        )
                        log_message(message, action="gelöscht (Nutzer informiert)", reason="Nachricht von Nicht-Whitelist Männer", deleted=True)

                        # Delete the sender's message after 10 seconds
                        time.sleep(10)
                        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                        # Delete the bot's message after 10 seconds
                        bot.delete_message(chat_id=message.chat.id, message_id=reply_message.message_id)
                    except Exception as e:
                        logger.warning(f"Couldn't delete message due to: {e}")
                        log_message(message, action="nicht gelöscht", reason="Fehler beim Löschen", deleted=False)
                        pass
            elif i == 270:
                if message.from_user.id in whitelistfemale or message.from_user.id in admins:
                    log_message(message, action="nicht gelöscht (Whitelist/Admin)",
                                reason="Nachricht von Whitelist oder Admin", deleted=False)
                else:
                    try:
                        # Send information as a reply to the message
                        reply_message = message.reply_text(
                            text="Schalom! Bitte beachte, dass dies kein allgemeiner Chat ist. Du wurdest entweder noch nicht Hinzugefügt oder bist keine Frau. Bitte schreibe bis dahin im Allgemeinen Chat. Und Bitte dort um Freischaltung.",
                            reply_to_message_id=message.message_id
                        )
                        log_message(message, action="gelöscht (Nutzer informiert)",
                                    reason="Nachricht von Nicht-Whitelist Frauen", deleted=True)

                        # Delete the sender's message after 10 seconds
                        time.sleep(10)
                        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

                        # Delete the bot's message after 10 seconds
                        bot.delete_message(chat_id=message.chat.id, message_id=reply_message.message_id)
                    except Exception as e:
                        logger.warning(f"Couldn't delete message due to: {e}")
                        log_message(message, action="nicht gelöscht", reason="Fehler beim Löschen", deleted=False)
                        pass

            else:
                log_message(message, action="nicht gelöscht", reason="Andere Themen-ID", deleted=False)


def add_to_whitelistsozialmedia(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zur Whitelist für soziale Medien hinzufügen möchtest.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    # Überprüfe, ob die Nachricht von einem Admin gesendet wurde
    admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]
    if message.from_user.id not in admins:
        reply_msg = update.message.reply_text("Du hast nicht die Berechtigung, jemanden zur Whitelist hinzuzufügen.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    whitelistsozialmedia.append(user_id)
    reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde zur Whitelist für soziale Medien hinzugefügt."
    log_message(message.reply_to_message, action="zur Whitelist für soziale Medien hinzugefügt", reason="Durch Admin-Befehl", deleted=False)

    sent_reply = update.message.reply_text(reply_msg)
    time.sleep(10)
    bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


def whitelist_user(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = update.message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zur Whitelist hinzufügen möchtest.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    # Überprüfe, ob die Nachricht von einem Admin gesendet wurde
    admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]
    if message.from_user.id not in admins:
        reply_msg = update.message.reply_text("Du hast nicht die Berechtigung, jemanden zur Whitelist hinzuzufügen.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    # Überprüfe die Argumente des Befehls
    if not context.args:
        reply_msg = update.message.reply_text("Bitte gib an, ob du den Nutzer zur Männer- oder Frauen-Gruppe hinzufügen möchtest: /whitelist sozialmedia , /whitelist frau oder /whitelist mann.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    gender = context.args[0].lower()

    if gender == "frau":
        whitelistfemale.append(user_id)
        reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde zur Frauen-Whitelist hinzugefügt."
        log_message(message.reply_to_message, action="zur Frauen-Whitelist hinzugefügt", reason="Durch Admin-Befehl", deleted=False)
    elif gender == "mann":
        whitelistmale.append(user_id)
        reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde zur Männer-Whitelist hinzugefügt."
        log_message(message.reply_to_message, action="zur Männer-Whitelist hinzugefügt", reason="Durch Admin-Befehl", deleted=False)
    elif gender == "sozialmedia":
        whitelistsozialmedia.append(user_id)
        reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde zur SozialMedia-Whitelist hinzugefügt."
        log_message(message.reply_to_message, action="zur SozialMedia-Whitelist hinzugefügt", reason="Durch Admin-Befehl", deleted=False)
    else:
        reply_msg = "Ungültiges Argument. Benutze /whitelist frau oder /whitelist mann."

    sent_reply = update.message.reply_text(reply_msg)
    time.sleep(10)
    bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    save_list_to_table(whitelistsozialmedia, "whitelistsozialmedia")
    save_list_to_table(whitelistfemale, "whitelistfemale")
    save_list_to_table(whitelistmale, "whitelistmale")

def add_to_supporter(update: Update, context: CallbackContext):
    message = update.message

    if not message.reply_to_message:
        reply_msg = message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du zum Unterstützer hinzufügen möchtest.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    user_id = message.reply_to_message.from_user.id
    user_name = message.reply_to_message.from_user.first_name

    admins = [admin.user.id for admin in bot.getChatAdministrators(message.chat.id)]
    if message.from_user.id not in admins:
        reply_msg = update.message.reply_text("Du hast nicht die Berechtigung, jemanden zum Unterstützer hinzuzufügen.")
        time.sleep(10)
        bot.delete_message(chat_id=message.chat.id, message_id=reply_msg.message_id)
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        return

    supporters.append(user_id)
    reply_msg = f"Benutzer {user_name} (ID: {user_id}) wurde als Unterstützer hinzugefügt."
    log_message(message.reply_to_message, action="als Unterstützer hinzugefügt", reason="Durch Admin-Befehl", deleted=False)

    sent_reply = update.message.reply_text(reply_msg)
    time.sleep(10)
    bot.delete_message(chat_id=message.chat.id, message_id=sent_reply.message_id)
    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    save_list_to_table(supporters, "supporter")


# ... (anderer Code bleibt gleich)

# Ein Dictionary um Warnungen für Nutzer zu speichern
user_warnings = {}

def save_warning_to_db(user_id, chat_id, reason):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO warnings (user_id, chat_id, reason) VALUES (%s, %s, %s)", (user_id, chat_id, reason))
    conn.commit()
    cursor.close()
    conn.close()

def warn_user(update: Update, context: CallbackContext):
    # Zugriff auf globale Liste warned_users
    global warned_users

    # Überprüfe, ob die Nachricht von einem Admin gesendet wurde
    admins = [admin.user.id for admin in context.bot.getChatAdministrators(update.message.chat.id)]
    if update.message.from_user.id not in admins:
        update.message.reply_text("Du hast nicht die Berechtigung, jemanden zu verwarnen.")
        return

    # Antwort auf die Nachricht des zu verwarnenden Nutzers
    if not update.message.reply_to_message:
        update.message.reply_text("Bitte antworte auf die Nachricht des Nutzers, den du verwarnen möchtest.")
        return

    user_id = update.message.reply_to_message.from_user.id
    reason = ' '.join(context.args)  # Grund für die Verwarnung aus den Befehlsargumenten extrahieren
    if not reason:
        update.message.reply_text("Bitte gib einen Grund für die Verwarnung an. Beispiel: `/warn Spamming`.")
        return

    # Wenn der Benutzer noch nicht in der warned_users-Liste ist, fügen wir ihn hinzu
    if user_id not in warned_users:
        warned_users.append(user_id)

    # Speichern der Warnung in der Datenbank
    save_warning_to_db(user_id, update.message.chat.id, reason)

    if len(warned_users) >= 3:  # Wenn der Benutzer 3 oder mehr Warnungen hat
        try:
            context.bot.kickChatMember(update.message.chat.id, user_id)
            update.message.reply_text(f"Benutzer wurde wegen 3 Warnungen gebannt!")
            warned_users.remove(user_id)  # Benutzer aus der Warnliste entfernen, da er gebannt wurde
        except Exception as e:
            update.message.reply_text(f"Fehler beim Bannen des Benutzers: {e}")
    else:
        update.message.reply_text(f"Benutzer wurde verwarnt! Anzahl der Verwarnungen: {len(warned_users)}")

    # Löschen der Befehlsnachricht und der Antwort des Bots nach 10 Sekunden
    time.sleep(10)
    context.bot.deleteMessage(update.message.chat_id, update.message.message_id)
    save_warning_to_db(user_id, update.message.chat.id, reason)


def extract_user_id(update: Update, context: CallbackContext) -> int:
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


def ban_user(update: Update, context: CallbackContext):
    user_id = extract_user_id(update, context)
    bot = context.bot
    chat_id = update.message.chat_id
    sender_id = update.message.from_user.id

    # Überprüfe, ob der Sender ein Admin ist
    admins = [admin.user.id for admin in bot.get_chat_administrators(chat_id)]
    if sender_id not in admins:
        response_msg = update.message.reply_text("Du hast nicht die Berechtigung, Benutzer zu bannen.")
    else:
        if not user_id:
            response_msg = update.message.reply_text("Du musst auf eine Nachricht eines Benutzers antworten oder seine Benutzer-ID angeben.")
        else:
            reason = ' '.join(context.args[1:]) if context.args else None
            try:
                update.message.chat.kick_member(user_id)
                response_msg = update.message.reply_text(f"Benutzer wurde gebannt! Grund: {reason if reason else 'Kein Grund angegeben.'}")
            except BadRequest as e:
                response_msg = update.message.reply_text(f"Fehler: {e.message}")
            except Exception as e:
                logger.warning(f"Couldn't ban user due to: {e}")
                response_msg = update.message.reply_text(f"Fehler: {e}")

    # Lösche die Befehlsnachricht und die Antwort des Bots nach 10 Sekunden
    time.sleep(10)
    bot.deleteMessage(chat_id, update.message.message_id)
    if response_msg:
        bot.deleteMessage(chat_id, response_msg.message_id)


# Einführung von zwei Dictionaries, um die Nachrichten pro Benutzer und die Verwarnungen zu speichern
user_message_count = {}


def check_spam(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Überprüfung, ob der Benutzer ein Admin ist
    admins = [admin.user.id for admin in bot.getChatAdministrators(chat_id)]
    if user_id in admins:
        return

    # Benutzerzähler aktualisieren
    if user_id not in user_message_count:
        user_message_count[user_id] = 0
    user_message_count[user_id] += 1

    # Nachrichtenzähler zurücksetzen, wenn es noch nicht geplant ist
    if user_id not in context.job_queue.jobs():
        context.job_queue.run_once(reset_count, 60, context=user_id)

    # Überprüfung, ob der Benutzer die Grenze überschritten hat
    if user_message_count[user_id] > 10:
        if user_id not in user_warnings:
            user_warnings[user_id] = 0
        user_warnings[user_id] += 1

        # Entscheidung, welche Nachricht zu senden ist, basierend auf der Anzahl der Verwarnungen
        if user_warnings[user_id] == 1:
            reply_message = update.message.reply_text(
                "Bitte sende nicht mehr als 10 Nachrichten pro Minute.",
                reply_to_message_id=update.message.message_id
            )
        else:
            reply_message = update.message.reply_text(
                "Spam erkannt vom System! Dies ist eine Verwarnung.",
                reply_to_message_id=update.message.message_id
            )
        time.sleep(10)
        bot.delete_message(chat_id=chat_id, message_id=reply_message.message_id)

def reset_count(context: CallbackContext):
    user_id = context.job.context
    user_message_count[user_id] = 0


def main():
    if not os.path.exists('log'):
        os.makedirs('log')
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f'log/log_{current_time}.log'
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    # Ein Beispiel für eine Info-Log-Nachricht
    logger.info('Das Programm wurde gestartet.')

    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, delete_general_messages))
    dispatcher.add_handler(CommandHandler('whitelist', whitelist_user, pass_args=True))
    dispatcher.add_handler(CommandHandler('addsupporter', add_to_supporter))
    dispatcher.add_handler(CommandHandler('warn', warn_user))
    dispatcher.add_handler(CommandHandler("ban", ban_user))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, check_spam))
    load_warned_users()
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
