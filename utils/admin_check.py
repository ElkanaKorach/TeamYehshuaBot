# Importiere das telegram-Modul
import telegram


# Definiere die Funktion is_admin, die überprüft, ob der Absender der Nachricht ein Admin ist
def is_admin(bot, update):
    # ID des Benutzers, der die Nachricht gesendet hat, speichern
    user_id = update.message.from_user.id

    # ID des Chats, in dem die Nachricht gesendet wurde, speichern
    chat_id = update.message.chat_id

    # Abrufen der Liste der Admins im Chat
    # Beachte: getChatAdministrators ist eine Methode des Bot-Objekts
    admins = bot.get_chat_administrators(chat_id)

    # Extrahieren und Speichern der IDs der Admins aus der Liste
    admin_ids = [admin.user.id for admin in admins]

    # Überprüfen, ob die user_id in der Liste der admin_ids ist
    # Gibt True zurück, wenn der Benutzer Admin ist, sonst False
    return user_id in admin_ids
