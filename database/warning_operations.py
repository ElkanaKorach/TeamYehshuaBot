from database.db_operations import logger, db_manager


def save_warning_to_db(user_id, chat_id, reason):
    conn = db_manager.create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO warnings (user_id, chat_id, reason) VALUES (?, ?, ?)", (user_id, chat_id, reason))
        conn.commit()
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Warnung in der Datenbank: {e}")
    finally:
        cursor.close()
        conn.close()

def load_warned_users_from_db():
    conn = db_manager.create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT DISTINCT user_id FROM warnings")
        users = cursor.fetchall()
        return [user[0] for user in users]
    except Exception as e:
        logger.error(f"Fehler beim Laden der verwarnten Benutzer aus der Datenbank: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
